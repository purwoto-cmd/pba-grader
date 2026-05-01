"""Wrapper LLM client provider-agnostic dengan throttle + retry.

Mendukung multiple provider via env var `PBA_PROVIDER`:

  groq         — Groq Cloud (default).            Auth: GROQ_API_KEY
  swiftrouter  — SwiftRouter (OpenAI-compatible). Auth: SWIFTROUTER_API_KEY
                 base_url: https://api.swiftrouter.com/v1
  bai          — B.AI (OpenAI-compatible).        Auth: BAI_API_KEY
                 base_url: https://api.b.ai/v1
  openai       — OpenAI langsung.                  Auth: OPENAI_API_KEY
  openai-compat — Endpoint OpenAI-compatible custom.
                 Wajib set: PBA_BASE_URL, PBA_API_KEY

Override base_url manual: set `PBA_BASE_URL` (akan di-pakai untuk swiftrouter/bai/openai-compat).

Wrapper ini:
- Memberi jeda minimum antar call (throttle).
- Retry exponential backoff + parsing `Retry-After` pada 429.
- Retry pada error koneksi sementara (5xx, network).
- 401/403/4xx lain langsung raise (nggak diretry).
"""

from __future__ import annotations

import json
import logging
import os
import random
import re
import threading
import time
from typing import Any, Callable

log = logging.getLogger(__name__)


# ---- Exception types: collect dari kedua SDK supaya bisa di-catch sekaligus ----

def _collect_exception_types() -> dict[str, tuple[type, ...]]:
    rate_limit: list[type] = []
    api_status: list[type] = []
    api_conn: list[type] = []

    try:
        from groq import APIConnectionError as G_Conn  # type: ignore
        from groq import APIStatusError as G_Stat  # type: ignore
        from groq import RateLimitError as G_Rate  # type: ignore

        rate_limit.append(G_Rate)
        api_status.append(G_Stat)
        api_conn.append(G_Conn)
    except ImportError:
        pass

    try:
        from openai import APIConnectionError as O_Conn  # type: ignore
        from openai import APIStatusError as O_Stat  # type: ignore
        from openai import RateLimitError as O_Rate  # type: ignore

        rate_limit.append(O_Rate)
        api_status.append(O_Stat)
        api_conn.append(O_Conn)
    except ImportError:
        pass

    return {
        "rate_limit": tuple(rate_limit) or (Exception,),
        "api_status": tuple(api_status) or (Exception,),
        "api_conn": tuple(api_conn) or (Exception,),
    }


_EXC = _collect_exception_types()


def _now() -> float:
    return time.monotonic()


def _parse_retry_after(exc: Exception) -> float | None:
    """Ambil hint detik tunggu dari header `retry-after` atau pesan error."""
    response = getattr(exc, "response", None)
    if response is not None:
        try:
            headers = getattr(response, "headers", None)
            if headers is not None:
                ra = headers.get("retry-after") or headers.get("Retry-After")
                if ra:
                    return float(ra)
        except Exception:  # noqa: BLE001
            pass
    msg = str(exc)
    m = re.search(r"try again in ([\d.]+)\s*([smh])", msg, re.IGNORECASE)
    if m:
        val = float(m.group(1))
        unit = m.group(2).lower()
        return val * {"s": 1, "m": 60, "h": 3600}[unit]
    m = re.search(r"retry[- ]?after[:= ]+([\d.]+)", msg, re.IGNORECASE)
    if m:
        return float(m.group(1))
    return None


# ---- Provider factory ----

DEFAULT_BASE_URLS = {
    "swiftrouter": "https://api.swiftrouter.com/v1",
    "bai": "https://api.b.ai/v1",
    "openai": "https://api.openai.com/v1",
}

# Mapping provider → nama env var API key utama (fallback ke PBA_API_KEY).
_PROVIDER_KEY_ENV = {
    "swiftrouter": "SWIFTROUTER_API_KEY",
    "bai": "BAI_API_KEY",
    "openai": "OPENAI_API_KEY",
}


def make_raw_client(provider: str | None = None):
    """Buat raw client (groq.Groq atau openai.OpenAI) sesuai provider."""
    provider = (provider or os.getenv("PBA_PROVIDER", "groq")).strip().lower()

    if provider == "groq":
        from groq import Groq

        return Groq()

    if provider in ("swiftrouter", "bai", "openai-compat", "openai"):
        from openai import OpenAI

        if provider in ("swiftrouter", "bai"):
            primary_env = _PROVIDER_KEY_ENV[provider]
            api_key = (
                os.getenv(primary_env)
                or os.getenv("PBA_API_KEY")
                or os.getenv("OPENAI_API_KEY")
            )
            base_url = os.getenv("PBA_BASE_URL") or DEFAULT_BASE_URLS[provider]
        elif provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY") or os.getenv("PBA_API_KEY")
            base_url = os.getenv("PBA_BASE_URL")  # boleh None → default OpenAI
        else:  # openai-compat
            api_key = os.getenv("PBA_API_KEY") or os.getenv("OPENAI_API_KEY")
            base_url = os.getenv("PBA_BASE_URL")
            if not base_url:
                raise ValueError(
                    "PBA_PROVIDER=openai-compat butuh PBA_BASE_URL untuk endpoint custom."
                )

        if not api_key:
            primary_env = _PROVIDER_KEY_ENV.get(provider)
            if primary_env:
                hint_keys = f"{primary_env} atau PBA_API_KEY"
            else:
                # openai-compat: factory di atas baca PBA_API_KEY → OPENAI_API_KEY.
                hint_keys = "PBA_API_KEY atau OPENAI_API_KEY"
            raise ValueError(
                f"API key untuk provider '{provider}' tidak ditemukan di env. "
                f"Set {hint_keys}."
            )

        kwargs: dict[str, Any] = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        return OpenAI(**kwargs)

    raise ValueError(
        f"PBA_PROVIDER='{provider}' tidak dikenal. "
        "Pakai salah satu: groq, swiftrouter, bai, openai, openai-compat."
    )


def get_provider_name(client: Any) -> str:
    """Tebak nama provider dari class client (untuk logging)."""
    cls = type(client).__module__.split(".", 1)[0]
    return cls or "unknown"


# ---- Throttled wrapper ----


class ThrottledLLMClient:
    """Thread-safe throttle + retry wrapper di atas client OpenAI-compatible.

    Drop-in lewat method `chat_completion(**kwargs)` yang mem-forward ke
    `client.chat.completions.create(**kwargs)`.
    """

    def __init__(
        self,
        client: Any | None = None,
        *,
        provider: str | None = None,
        min_interval_s: float | None = None,
        max_retries: int | None = None,
        max_backoff_s: float = 60.0,
    ):
        self.client = client or make_raw_client(provider)
        self.provider = provider or os.getenv("PBA_PROVIDER", "groq").lower()
        self.min_interval_s = (
            min_interval_s
            if min_interval_s is not None
            else float(os.getenv("PBA_THROTTLE_S", "1.2"))
        )
        self.max_retries = (
            max_retries if max_retries is not None else int(os.getenv("PBA_MAX_RETRIES", "8"))
        )
        self.max_backoff_s = max_backoff_s
        self._last_call_at: float = 0.0
        self._lock = threading.Lock()

    # ---- Throttle ----

    def _wait_for_slot(self) -> None:
        with self._lock:
            elapsed = _now() - self._last_call_at
            if elapsed < self.min_interval_s:
                time.sleep(self.min_interval_s - elapsed)
            self._last_call_at = _now()

    # ---- Retry ----

    def _call_with_retry(self, fn: Callable[[], Any], *, label: str) -> Any:
        attempt = 0
        while True:
            self._wait_for_slot()
            try:
                return fn()
            except _EXC["rate_limit"] as exc:
                wait = _parse_retry_after(exc)
                if wait is None:
                    wait = min(self.max_backoff_s, (2**attempt) + random.uniform(0, 1))
                else:
                    wait = min(self.max_backoff_s, wait + random.uniform(0, 1))
                log.warning(
                    "[%s] rate-limited (attempt %d/%d) — tunggu %.1fs",
                    label,
                    attempt + 1,
                    self.max_retries,
                    wait,
                )
                time.sleep(wait)
            except _EXC["api_conn"] as exc:
                wait = min(self.max_backoff_s, (2**attempt) + random.uniform(0, 1))
                log.warning(
                    "[%s] connection error (attempt %d/%d) — tunggu %.1fs: %s",
                    label,
                    attempt + 1,
                    self.max_retries,
                    wait,
                    exc,
                )
                time.sleep(wait)
            except _EXC["api_status"] as exc:
                status = getattr(exc, "status_code", None) or getattr(
                    getattr(exc, "response", None), "status_code", None
                )
                if status and 500 <= status < 600:
                    wait = min(self.max_backoff_s, (2**attempt) + random.uniform(0, 1))
                    log.warning(
                        "[%s] server error %s (attempt %d/%d) — tunggu %.1fs",
                        label,
                        status,
                        attempt + 1,
                        self.max_retries,
                        wait,
                    )
                    time.sleep(wait)
                else:
                    # 401/403/4xx lain → langsung raise, retry sia-sia
                    raise
            attempt += 1
            if attempt > self.max_retries:
                raise RuntimeError(
                    f"[{label}] retry budget habis setelah {self.max_retries} attempt"
                )

    # ---- Public API ----

    def chat_completion(self, **kwargs: Any) -> Any:
        """Forward ke client.chat.completions.create(**kwargs) + retry+throttle."""
        label = kwargs.get("model", self.provider)
        return self._call_with_retry(
            lambda: self.client.chat.completions.create(**kwargs),
            label=label,
        )


def normalize_message_content(content: Any) -> str:
    """Konversi message.content menjadi string yang bisa di-parse downstream.

    Beberapa provider (notably SwiftRouter untuk model tertentu seperti
    `llama-4-scout`) mengembalikan `message.content` sebagai dict alih-alih str
    — biasanya karena routing internal mereka memakai function-calling shim.

    Bentuk yang sudah ditemui:
    - str biasa (Groq, OpenAI, gpt-oss-120b di SwiftRouter): `'{...}'`
    - dict langsung: `{'is_screenshot_ai': False, 'notes': '...'}`
    - dict function-call wrap: `{'name': 'output_json',
                                  'parameters': {'json': {...}},
                                  'type': 'function'}`

    Helper ini selalu mengembalikan string JSON / teks supaya downstream
    `json.loads(...)` atau regex extraction tetap kompatibel.
    """
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, dict):
        # Bentuk function-call wrapper SwiftRouter
        params = content.get("parameters") if isinstance(content.get("parameters"), dict) else None
        if params and isinstance(params.get("json"), (dict, list)):
            return json.dumps(params["json"], ensure_ascii=False)
        # Dict JSON langsung — serialize as-is
        return json.dumps(content, ensure_ascii=False)
    if isinstance(content, list):
        # Beberapa SDK return list of content parts. Concat text parts.
        parts = []
        for p in content:
            if isinstance(p, dict):
                txt = p.get("text") or p.get("content")
                if isinstance(txt, str):
                    parts.append(txt)
            elif isinstance(p, str):
                parts.append(p)
        return "".join(parts)
    return str(content)


# Backward-compat alias agar kode lama (ThrottledGroqClient) masih jalan.
ThrottledGroqClient = ThrottledLLMClient
