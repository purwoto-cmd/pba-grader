"""Pydantic models untuk data pipeline grading."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

Versi = Literal["D", "E", "UNKNOWN"]
Level = Literal["sangat_baik", "baik", "cukup", "kurang", "tidak_dijawab"]

SOAL_IDS = ["1.1", "1.2", "1.3", "2.1", "2.2", "2.3", "3.1", "3.2"]


class ExtractedImage(BaseModel):
    """Gambar/screenshot yang di-embed di PDF mahasiswa."""

    page: int
    index_in_page: int
    path: Path
    width: int
    height: int
    # Soal mana yang kemungkinan terkait (ditentukan oleh segmentasi)
    soal_id: str | None = None

    model_config = {"arbitrary_types_allowed": True}


class PageText(BaseModel):
    page: int
    text: str
    # True jika teks diambil via OCR (bukan layer teks PDF asli)
    via_ocr: bool = False


class IngestResult(BaseModel):
    pdf_path: Path
    pages: list[PageText]
    images: list[ExtractedImage]
    full_text: str

    model_config = {"arbitrary_types_allowed": True}


class Identity(BaseModel):
    nama: str | None = None
    nim: str | None = None
    versi: Versi = "UNKNOWN"
    versi_confidence: float = 0.0
    # Catatan deteksi (e.g. alasan versi ditetapkan UNKNOWN)
    notes: list[str] = Field(default_factory=list)


class SoalAnswer(BaseModel):
    soal_id: str
    raw_text: str
    word_count: int = 0
    # Screenshot yang terkait dengan soal ini (hanya 2.2 dan 2.3)
    images: list[ExtractedImage] = Field(default_factory=list)

    model_config = {"arbitrary_types_allowed": True}


class SoalScore(BaseModel):
    soal_id: str
    bobot: float  # 0-100 persen
    level: Level
    skor_0_100: float  # 0-100, skor mentah dari rubrik
    skor_terbobot: float  # skor_0_100 * bobot / 100
    evidensi: list[str] = Field(default_factory=list)
    feedback: str = ""
    # Raw JSON response dari judge untuk audit
    raw_judge: dict = Field(default_factory=dict)
    # Self-consistency: jumlah sample yang digunakan (1 untuk default, 3+ untuk soal bobot tinggi)
    n_samples: int = 1
    samples_skor: list[float] = Field(default_factory=list)
    # True jika jawaban kosong / tidak terdeteksi
    kosong: bool = False


class StudentResult(BaseModel):
    pdf_path: Path
    identity: Identity
    answers: dict[str, SoalAnswer] = Field(default_factory=dict)
    scores: dict[str, SoalScore] = Field(default_factory=dict)
    total: float = 0.0
    total_level: Level = "kurang"
    # Flag untuk review manual
    flags: list[str] = Field(default_factory=list)
    # Waktu grading (detik)
    elapsed_s: float = 0.0

    model_config = {"arbitrary_types_allowed": True}


class PlagiarismFlag(BaseModel):
    pdf_a: Path
    pdf_b: Path
    soal_id: str
    cosine_similarity: float

    model_config = {"arbitrary_types_allowed": True}
