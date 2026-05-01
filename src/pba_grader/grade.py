"""LLM-as-judge berbasis rubrik menggunakan Groq API.

Untuk setiap soal, judge menerima:
  - Rubrik lengkap (4 level + deskripsi level)
  - Kunci jawaban referensi (dari keys/key_D.md atau key_E.md)
  - Jawaban mahasiswa (teks)
  - Metadata soal (bobot, tipe, elemen wajib)

dan menghasilkan structured JSON:
  {
    "level": "sangat_baik|baik|cukup|kurang",
    "skor_0_100": 0-100,
    "evidensi": ["...", "..."],
    "feedback": "...",
  }

Untuk soal dengan bobot >= 15% (2.2, 2.3, 3.1), gunakan self-consistency:
  jalankan 3× → ambil median skor → level mengikuti skor median.
"""

from __future__ import annotations

import json
import logging
import os
import re
import statistics
from pathlib import Path
from typing import Any

import yaml

from .llm_client import ThrottledLLMClient, make_raw_client, normalize_message_content
from .schema import Level, SoalAnswer, SoalScore

log = logging.getLogger(__name__)

# --- Model config ---
# Default model bergantung provider. Set via env var atau biarkan default Groq.
_PROVIDER = os.getenv("PBA_PROVIDER", "groq").lower()
_DEFAULTS_BY_PROVIDER = {
    "groq": {
        "text": "llama-3.3-70b-versatile",
        "reasoning": "openai/gpt-oss-120b",
    },
    "swiftrouter": {
        # Model ID SwiftRouter (verified dari swiftrouter.com/models, Apr 2026).
        # gpt-oss-120b: reasoning, $0.04/$0.19 per 1M, 131K context — paling worth it.
        "text": "gpt-oss-120b",
        "reasoning": "gpt-oss-120b",
    },
    "bai": {
        # Model ID B.AI (https://docs.b.ai/llmservice/models/).
        # Default: gpt-5.4-mini ($0.75/$4.50 per 1M, multimodal). Verified end-to-end
        # untuk rubric grading bilingual ID/AR — nggak butuh top-up tier premium.
        # Upgrade ke claude-sonnet-4.5 / claude-haiku-4.5 butuh deposit; override:
        #   PBA_MODEL_TEXT=claude-sonnet-4.5 PBA_MODEL_REASONING=claude-sonnet-4.5
        "text": "gpt-5.4-mini",
        "reasoning": "gpt-5.4-mini",
    },
    "openai": {
        "text": "gpt-4o-mini",
        "reasoning": "gpt-4o",
    },
}
_DEFAULTS = _DEFAULTS_BY_PROVIDER.get(_PROVIDER, _DEFAULTS_BY_PROVIDER["groq"])
MODEL_TEXT = os.getenv("PBA_MODEL_TEXT", _DEFAULTS["text"])
MODEL_REASONING = os.getenv("PBA_MODEL_REASONING", _DEFAULTS["reasoning"])

# Bobot minimal untuk pakai self-consistency (3x sampling)
SELF_CONSISTENCY_MIN_BOBOT = 15

LEVEL_TO_SCORE_RANGE: dict[Level, tuple[float, float]] = {
    "sangat_baik": (85.0, 100.0),
    "baik": (70.0, 84.9),
    "cukup": (60.0, 69.9),
    "kurang": (0.0, 59.9),
    "tidak_dijawab": (0.0, 0.0),
}


def score_to_level(score: float) -> Level:
    if score >= 85:
        return "sangat_baik"
    if score >= 70:
        return "baik"
    if score >= 60:
        return "cukup"
    return "kurang"


# --- Prompt templates ---

SYSTEM_PROMPT = """Anda adalah dosen bahasa Arab yang bertugas menilai jawaban UTS mahasiswa \
mata kuliah "Artificial Intelligence dalam Pendidikan Bahasa Arab" berdasarkan rubrik yang sudah \
diberikan. Anda HARUS:

1. Menilai secara objektif sesuai rubrik 4-level (sangat_baik, baik, cukup, kurang).
2. Memberi kredit untuk temuan lain yang valid, tidak hanya yang persis sama dengan kunci referensi.
3. Memberi feedback konkret dan actionable dalam bahasa Indonesia.
4. Mengembalikan HANYA JSON valid sesuai skema yang diminta, tanpa penjelasan tambahan.
5. Jika jawaban mahasiswa kosong atau tidak menjawab, tetapkan level "kurang" dan skor 0.
6. Jangan terlalu ketat untuk variasi bahasa (Indonesia/Arab) — fokus ke isi dan substansi.
"""

USER_TEMPLATE = """# Soal {soal_id} — {nama_soal}

## Rubrik

Fase: {fase} (bobot total fase: {bobot_fase}%)
Bobot soal ini: {bobot_soal}% dari total nilai UTS
Tipe: {tipe}

### Aspek yang dinilai
{aspek_dinilai}

### Level penilaian (dari rubrik resmi)
- **sangat_baik** (85-100): {level_sangat_baik}
- **baik** (70-84): {level_baik}
- **cukup** (60-69): {level_cukup}
- **kurang** (<60): {level_kurang}

{extra_rules}

## Kunci Jawaban Referensi (tidak mutlak, dosen dapat menerima jawaban lain yang valid)

{kunci_referensi}

## Jawaban Mahasiswa

Jumlah kata: {word_count}
{word_count_note}

```
{jawaban_mahasiswa}
```

## Instruksi Penilaian

Nilai jawaban di atas berdasarkan rubrik. Kembalikan **HANYA JSON** dengan skema:

```json
{{
  "level": "sangat_baik" | "baik" | "cukup" | "kurang",
  "skor_0_100": <angka 0-100>,
  "evidensi": ["kutipan singkat dari jawaban yang mendukung skor", "..."],
  "feedback": "1-3 kalimat feedback konkret untuk mahasiswa dalam bahasa Indonesia"
}}
```

Pastikan skor konsisten dengan level:
- sangat_baik → 85-100
- baik → 70-84
- cukup → 60-69
- kurang → 0-59

Gunakan bagian paling atas dari range jika kualitas jawaban di batas atas level tsb, dst.
"""


class Judge:
    """LLM-as-judge wrapper."""

    def __init__(
        self,
        rubric_path: Path,
        key_d_path: Path,
        key_e_path: Path,
        client: ThrottledLLMClient | Any | None = None,
        *,
        enable_self_consistency: bool = True,
    ):
        self.rubric = yaml.safe_load(Path(rubric_path).read_text())
        self.soal_by_id = {s["id"]: s for s in self.rubric["soal"]}
        self.key_d = Path(key_d_path).read_text()
        self.key_e = Path(key_e_path).read_text()
        if isinstance(client, ThrottledLLMClient):
            self.client = client
        elif client is not None:
            self.client = ThrottledLLMClient(client=client)
        else:
            self.client = ThrottledLLMClient()
        self.enable_self_consistency = enable_self_consistency

    # ---- Public API ----

    def grade_soal(
        self,
        soal_id: str,
        answer: SoalAnswer,
        versi: str,
    ) -> SoalScore:
        soal = self.soal_by_id[soal_id]
        bobot = soal["bobot"]

        # --- Pre-checks yang deterministik ---
        if not answer.raw_text.strip():
            return SoalScore(
                soal_id=soal_id,
                bobot=bobot,
                level="kurang",
                skor_0_100=0.0,
                skor_terbobot=0.0,
                evidensi=[],
                feedback="Jawaban tidak ditemukan di PDF. Periksa apakah mahasiswa menulis jawaban untuk soal ini.",
                kosong=True,
            )

        # Word count hard rule untuk soal 3.1
        word_count_note = ""
        word_count_penalty = 0.0
        if soal_id == "3.1":
            wc = answer.word_count
            wmin = soal.get("batas_kata", {}).get("min", 200)
            wmax = soal.get("batas_kata", {}).get("max", 300)
            if wc < wmin:
                word_count_note = (
                    f"PERHATIAN: jawaban hanya {wc} kata, di bawah minimum {wmin}. "
                    "Rubrik menyatakan refleksi di bawah batas kata otomatis masuk level 'kurang'."
                )
                word_count_penalty = 15.0  # cap downgrade
            elif wc > wmax + 50:
                word_count_note = (
                    f"CATATAN: jawaban {wc} kata, di atas maksimum {wmax}."
                )

        # --- Pilih model & sampling strategy ---
        use_self_consistency = self.enable_self_consistency and bobot >= SELF_CONSISTENCY_MIN_BOBOT
        model = MODEL_REASONING if use_self_consistency else MODEL_TEXT
        n_samples = 3 if use_self_consistency else 1

        # --- Build prompt ---
        user_prompt = self._build_user_prompt(
            soal, answer, versi, word_count_note
        )

        # --- Sampling ---
        samples: list[dict[str, Any]] = []
        for i in range(n_samples):
            raw = self._call_judge(model, user_prompt, temperature=0.0 if i == 0 else 0.3)
            parsed = self._parse_judge_output(raw)
            if parsed is not None:
                samples.append(parsed)

        if not samples:
            return SoalScore(
                soal_id=soal_id,
                bobot=bobot,
                level="kurang",
                skor_0_100=0.0,
                skor_terbobot=0.0,
                evidensi=[],
                feedback="[Error: judge tidak mengembalikan JSON valid, butuh review manual]",
            )

        # --- Aggregate ---
        skor_list = [float(s.get("skor_0_100", 0.0)) for s in samples]
        median_skor = statistics.median(skor_list)
        median_skor = max(0.0, min(100.0, median_skor - word_count_penalty))
        level = score_to_level(median_skor)

        # Ambil feedback & evidensi dari sample dengan skor paling dekat ke median
        canonical = min(samples, key=lambda s: abs(float(s.get("skor_0_100", 0.0)) - median_skor))
        evidensi = list(canonical.get("evidensi", []))
        feedback = str(canonical.get("feedback", "")).strip()
        if word_count_note:
            feedback = f"{word_count_note}\n{feedback}".strip()

        return SoalScore(
            soal_id=soal_id,
            bobot=bobot,
            level=level,
            skor_0_100=median_skor,
            skor_terbobot=median_skor * bobot / 100.0,
            evidensi=evidensi,
            feedback=feedback,
            raw_judge={"samples": samples, "model": model},
            n_samples=len(samples),
            samples_skor=skor_list,
        )

    # ---- Internals ----

    def _build_user_prompt(
        self,
        soal: dict[str, Any],
        answer: SoalAnswer,
        versi: str,
        word_count_note: str,
    ) -> str:
        fase_id = soal["fase"]
        fase = self.rubric["fase"][fase_id]
        level = soal["level"]

        aspek = "\n".join(f"- {a}" for a in soal.get("aspek_dinilai", []))

        extra_rules = []
        if soal.get("dimensi_wajib"):
            extra_rules.append(
                "Dimensi WAJIB dianalisis: "
                + ", ".join(soal["dimensi_wajib"])
            )
        if soal.get("elemen_wajib"):
            extra_rules.append(
                "Elemen WAJIB dalam prompt: "
                + "; ".join(soal["elemen_wajib"])
            )
        if soal.get("min_temuan"):
            extra_rules.append(
                f"Minimal temuan yang diharapkan: {soal['min_temuan']}"
            )
        if soal.get("sub_bagian"):
            sb = soal["sub_bagian"]
            if isinstance(sb, dict):
                extra_rules.append(
                    "Sub-bagian soal: " + "; ".join(f"{k}) {v}" for k, v in sb.items())
                )
            else:
                extra_rules.append(f"Soal terdiri dari {sb} sub-bagian.")
        if soal.get("pertanyaan_dijawab"):
            extra_rules.append(
                "Sub-pertanyaan yang harus dijawab:\n"
                + "\n".join(f"  - {q}" for q in soal["pertanyaan_dijawab"])
            )
        extra = "\n\n### Aturan tambahan\n" + "\n".join(f"- {r}" for r in extra_rules) if extra_rules else ""

        kunci = self.key_d if versi == "D" else self.key_e if versi == "E" else (self.key_d + "\n\n---\n\n" + self.key_e)

        # Potong kunci ke bagian yang relevan (berdasarkan ID soal) untuk hemat token
        kunci_soal = self._slice_kunci_for_soal(kunci, soal["id"])

        return USER_TEMPLATE.format(
            soal_id=soal["id"],
            nama_soal=soal["nama"],
            fase=fase["nama"],
            bobot_fase=fase["bobot_total"],
            bobot_soal=soal["bobot"],
            tipe=soal.get("tipe", ""),
            aspek_dinilai=aspek or "- (tidak ada aspek spesifik selain rubrik)",
            level_sangat_baik=level["sangat_baik"],
            level_baik=level["baik"],
            level_cukup=level["cukup"],
            level_kurang=level["kurang"],
            extra_rules=extra,
            kunci_referensi=kunci_soal or "(tidak ada kunci referensi spesifik untuk soal ini)",
            jawaban_mahasiswa=answer.raw_text[:6000],  # cap panjang
            word_count=answer.word_count,
            word_count_note=word_count_note,
        )

    @staticmethod
    def _slice_kunci_for_soal(kunci_full: str, soal_id: str) -> str:
        """Ambil bagian kunci yang relevan untuk soal_id (heuristik heading)."""
        # Cari heading "Soal 1.1", lalu ambil sampai heading "Soal X.X" berikutnya atau akhir
        pat = re.compile(rf"^##\s*Soal\s*{re.escape(soal_id)}\b.*?(?=^##\s*Soal\s|\Z)", re.MULTILINE | re.DOTALL)
        m = pat.search(kunci_full)
        if m:
            return m.group(0).strip()
        return ""

    def _call_judge(self, model: str, user_prompt: str, temperature: float = 0.0) -> str:
        resp = self.client.chat_completion(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_completion_tokens=1200,
            response_format={"type": "json_object"},
        )
        return normalize_message_content(resp.choices[0].message.content)

    @staticmethod
    def _parse_judge_output(raw: str) -> dict[str, Any] | None:
        raw = raw.strip()
        # Buang code fence jika ada
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw)
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            log.warning("Gagal parse JSON judge output: %s", raw[:200])
            return None
        if not isinstance(data, dict):
            return None
        # Sanity check fields
        if "skor_0_100" not in data or "level" not in data:
            return None
        try:
            data["skor_0_100"] = float(data["skor_0_100"])
        except (TypeError, ValueError):
            return None
        if data["level"] not in ("sangat_baik", "baik", "cukup", "kurang"):
            data["level"] = score_to_level(data["skor_0_100"])
        return data
