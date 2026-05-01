"""Penilaian screenshot output AI pada soal 2.2 & 2.3 menggunakan Llama 4 Scout (vision).

Strategi:
  - Untuk tiap gambar yang dipetakan ke soal 2.2 atau 2.3:
    - Kirim ke vision model dengan prompt: "Apakah ini screenshot output AI chatbot berisi
      bahan ajar bahasa Arab? Apakah outputnya koheren dengan prompt yang diklaim mahasiswa?"
  - Agregasi hasil vision ke dalam score soal 2.2/2.3 sebagai sinyal tambahan
    (bukan pengganti grading teks).
"""

from __future__ import annotations

import base64
import logging
import os
from pathlib import Path
from typing import Any

from .llm_client import ThrottledLLMClient, normalize_message_content
from .schema import ExtractedImage

log = logging.getLogger(__name__)

_PROVIDER_V = os.getenv("PBA_PROVIDER", "groq").lower()
_VISION_DEFAULTS = {
    "groq": "meta-llama/llama-4-scout-17b-16e-instruct",
    "swiftrouter": "llama-4-scout",  # $0.08/$0.30 per 1M, 328K context, multimodal
    # B.AI: claude-haiku-4.5 paling murah yang multimodal ($1.10/$5.50 per 1M).
    "bai": "claude-haiku-4.5",
    "openai": "gpt-4o-mini",
}
MODEL_VISION = os.getenv(
    "PBA_MODEL_VISION", _VISION_DEFAULTS.get(_PROVIDER_V, _VISION_DEFAULTS["groq"])
)

VISION_PROMPT = """Anda menilai screenshot output AI chatbot yang dilampirkan mahasiswa \
di UTS prompt engineering bahasa Arab.

Konteks: mahasiswa diminta membuat prompt untuk menghasilkan bahan ajar bahasa Arab \
(teks bacaan/dialog/soal) untuk tema "{tema}". Screenshot ini diklaim sebagai output AI dari \
prompt {versi_prompt} yang mereka rancang.

Nilai screenshot ini dengan JSON:

```json
{{
  "is_screenshot_ai": true/false,
  "contains_arabic_content": true/false,
  "relevant_to_tema": true/false,
  "quality": "bagus" | "sedang" | "buruk" | "tidak_relevan",
  "notes": "1-2 kalimat catatan singkat"
}}
```

Kriteria:
- is_screenshot_ai: apakah ini jelas screenshot UI chatbot AI (ChatGPT, Claude, Gemini, dll) atau output AI text?
- contains_arabic_content: apakah ada teks Arab / nama Arab dalam output?
- relevant_to_tema: apakah isinya berkaitan dengan tema {tema}?
- quality: kualitas bahan ajar yang dihasilkan AI (bagus/sedang/buruk/tidak_relevan).

Jawab HANYA JSON, tanpa teks lain.
"""


def _encode_image_to_data_url(path: Path) -> str:
    data = path.read_bytes()
    ext = path.suffix.lstrip(".").lower() or "png"
    if ext == "jpg":
        ext = "jpeg"
    b64 = base64.b64encode(data).decode()
    return f"data:image/{ext};base64,{b64}"


class VisionGrader:
    def __init__(self, client: ThrottledLLMClient | Any | None = None):
        if isinstance(client, ThrottledLLMClient):
            self.client = client
        elif client is not None:
            self.client = ThrottledLLMClient(client=client)
        else:
            self.client = ThrottledLLMClient()

    def grade_screenshot(
        self,
        img: ExtractedImage,
        tema: str,
        versi_prompt: str = "V1",
    ) -> dict[str, Any] | None:
        data_url = _encode_image_to_data_url(img.path)
        prompt = VISION_PROMPT.format(tema=tema, versi_prompt=versi_prompt)
        try:
            resp = self.client.chat_completion(
                model=MODEL_VISION,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": data_url}},
                        ],
                    }
                ],
                temperature=0.0,
                max_completion_tokens=400,
                response_format={"type": "json_object"},
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("Vision call gagal untuk %s: %s", img.path.name, exc)
            return None
        raw = normalize_message_content(resp.choices[0].message.content).strip()
        try:
            import json
            return json.loads(raw)
        except Exception as exc:  # noqa: BLE001
            log.warning("Vision output non-JSON untuk %s: %s (raw=%s)", img.path.name, exc, raw[:200])
            return None

    def summarize_for_soal(
        self,
        images: list[ExtractedImage],
        tema: str,
        versi_prompt: str,
    ) -> dict[str, Any]:
        """Ringkas hasil vision utk semua gambar pada satu soal menjadi sinyal singkat."""
        if not images:
            return {"n_images": 0, "has_valid_screenshot": False, "per_image": []}
        per = []
        for img in images:
            res = self.grade_screenshot(img, tema, versi_prompt)
            per.append({"path": str(img.path), **(res or {"error": "no_response"})})
        has_valid = any(
            r.get("is_screenshot_ai") and r.get("relevant_to_tema") for r in per
        )
        return {"n_images": len(images), "has_valid_screenshot": has_valid, "per_image": per}
