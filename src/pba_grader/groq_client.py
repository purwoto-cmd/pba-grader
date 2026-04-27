"""Wrapper Groq client dengan throttle + retry untuk handle rate limit free tier.

Karena Groq free tier punya batas 30 RPM (untuk llama-3.3-70b dan kelas yang sama),
batch 66 mahasiswa × 8 soal × 1-3 sample bisa overload kalau di-burst tanpa jeda.

Wrapper ini:
- Memberi jeda minimum antar call (default 1.2 detik → ~50 RPM, di atas free tier
  tapi di-clamp oleh retry kalau Groq nge-429).
- Retry dengan exponential backoff + Retry-After header parsing kalau dapat 429.
- Retry pada error koneksi sementara (timeout, 5xx).
"""

from __future__ import annotations

import logging
import os
import random
import re
import threading
import time
from typing import Any, Callable

from groq import APIConnectionError, APIStatusError, Groq, RateLimitError

log = logging.getLogger(__name__)


def _now() -> float:
    return time.monotonic()


def _parse_retry_after(exc: Exception) -> float | None:
    """Coba ambil hint detik tunggu dari header `retry-after` atau pesan error."""
    headers = getattr(exc, "response", None)
    if headers is not None:
        try:
            ra = headers.headers.get("retry-after") or headers.headers.get("Retry-After")
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


class ThrottledGroqClient:
    """Thread-safe throttle + retry wrapper di atas `groq.Groq`.

    Pakai sebagai drop-in untuk client.chat.completions.create(...)
    melalui method `chat_completion(**kwargs)`.
    """

    def __init__(
        self,
        client: Groq | None = None,
        *,
        min_interval_s: float | None = None,
        max_retries: int | None = None,
        max_backoff_s: float = 60.0,
    ):
        self.client = client or Groq()
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
            except RateLimitError as exc:
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
            except (APIConnectionError, APIStatusError) as exc:
                status = getattr(exc, "status_code", None) or getattr(
                    getattr(exc, "response", None), "status_code", None
                )
                # Retry hanya kalau 5xx atau koneksi
                if isinstance(exc, APIConnectionError) or (status and 500 <= status < 600):
                    wait = min(self.max_backoff_s, (2**attempt) + random.uniform(0, 1))
                    log.warning(
                        "[%s] error transient %s (attempt %d/%d) — tunggu %.1fs",
                        label,
                        status or "conn",
                        attempt + 1,
                        self.max_retries,
                        wait,
                    )
                    time.sleep(wait)
                else:
                    raise
            attempt += 1
            if attempt > self.max_retries:
                raise RuntimeError(
                    f"[{label}] retry budget habis setelah {self.max_retries} attempt"
                )

    # ---- Public API ----

    def chat_completion(self, **kwargs: Any) -> Any:
        """Drop-in untuk client.chat.completions.create(**kwargs) dengan retry+throttle."""
        label = kwargs.get("model", "groq")
        return self._call_with_retry(
            lambda: self.client.chat.completions.create(**kwargs),
            label=label,
        )
