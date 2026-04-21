"""Deteksi identitas mahasiswa dan versi UTS (D vs E)."""

from __future__ import annotations

import re

from .schema import Identity, IngestResult

# Keyword khas tiap versi (dari dokumen soal)
KEYWORDS_D = [
    "Berbelanja di Pasar",
    "التسوق في السوق",
    "في السوق",
    "belanja di pasar",
    "البائع",
    "الطماطم",
    "الثوم",
    "Chain-of-Thought",  # pertanyaan 3.2a Versi D
    "AraBERT",  # pertanyaan 3.2b Versi D
    "LLM umum vs",  # pertanyaan 3.2b Versi D
]

KEYWORDS_E = [
    "في المطار",
    "bandara",
    "المسافرون",
    "عنبر الطائرة",
    "ضواحي",
    "check-in",
    "zero-shot prompting",  # pertanyaan 3.2a Versi E
    "few-shot prompting",  # pertanyaan 3.2a Versi E
    "tantangan khusus dalam pemrosesan NLP",  # pertanyaan 3.2b Versi E
]

NIM_PATTERN = re.compile(r"\b(\d{8,15})\b")
NAMA_PATTERNS = [
    re.compile(r"Nama\s*(?:Mahasiswa)?\s*[:：]\s*([^\n\r]+)", re.IGNORECASE),
    re.compile(r"Nama\s*(?:Mahasiswa)?\s*\n([^\n\r]+)", re.IGNORECASE),
]
NIM_LABEL_PATTERNS = [
    re.compile(r"NIM\s*[:：]\s*(\d{8,15})", re.IGNORECASE),
    re.compile(r"NIM\s*\n\s*(\d{8,15})", re.IGNORECASE),
]


def _normalize(text: str) -> str:
    return text.lower()


def detect_version(text: str) -> tuple[str, float, list[str]]:
    """Return (versi, confidence, notes)."""
    text_lc = _normalize(text)
    hits_d = sum(1 for kw in KEYWORDS_D if kw.lower() in text_lc)
    hits_e = sum(1 for kw in KEYWORDS_E if kw.lower() in text_lc)
    notes = [f"keyword hits D={hits_d}, E={hits_e}"]

    if hits_d == 0 and hits_e == 0:
        return "UNKNOWN", 0.0, notes + ["Tidak ada keyword versi yang terdeteksi"]
    if hits_d > hits_e:
        conf = hits_d / (hits_d + hits_e) if (hits_d + hits_e) else 0.0
        return "D", conf, notes
    if hits_e > hits_d:
        conf = hits_e / (hits_d + hits_e) if (hits_d + hits_e) else 0.0
        return "E", conf, notes
    return "UNKNOWN", 0.5, notes + ["Keyword D dan E seimbang, butuh review manual"]


def detect_nim(text: str) -> str | None:
    for pat in NIM_LABEL_PATTERNS:
        m = pat.search(text)
        if m:
            return m.group(1).strip()
    # Fallback: pertama ditemukan 8-15 digit setelah kata 'NIM'
    m = re.search(r"NIM[\s\S]{0,60}?(\d{8,15})", text, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return None


def detect_nama(text: str) -> str | None:
    for pat in NAMA_PATTERNS:
        m = pat.search(text)
        if m:
            candidate = m.group(1).strip()
            # Hapus underscore pengisian form kosong
            candidate = candidate.strip("_ \t")
            if candidate and not candidate.startswith("_") and len(candidate) <= 100:
                return candidate
    return None


def detect_identity(ingest: IngestResult) -> Identity:
    """Deteksi identitas + versi dari hasil ingest PDF."""
    text = ingest.full_text
    versi, conf, notes = detect_version(text)
    nama = detect_nama(text)
    nim = detect_nim(text)
    if not nama:
        notes.append("Nama tidak terdeteksi otomatis")
    if not nim:
        notes.append("NIM tidak terdeteksi otomatis")
    return Identity(nama=nama, nim=nim, versi=versi, versi_confidence=conf, notes=notes)
