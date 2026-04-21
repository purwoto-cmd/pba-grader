"""Segmentasi teks PDF mahasiswa menjadi jawaban per soal.

Strategi: cari anchor heading (regex) untuk setiap soal, lalu ambil teks
antara anchor-nya sampai anchor berikutnya.

Anchor utama: "Soal 1.1", "Soal 1.2", ..., "Soal 3.2".
Juga tolerir variasi seperti "1.1", "Jawaban 1.1", "1.1.", dst.

Untuk gambar (screenshot), kita petakan ke soal 2.2 atau 2.3 berdasarkan
halaman — gambar yang muncul di halaman antara anchor 2.2 dan 2.3 akan
masuk ke 2.2, dst.
"""

from __future__ import annotations

import re

from .schema import ExtractedImage, IngestResult, SoalAnswer

SOAL_IDS = ["1.1", "1.2", "1.3", "2.1", "2.2", "2.3", "3.1", "3.2"]

# Anchor fleksibel. Urutan penting — yang lebih spesifik dulu.
ANCHOR_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    sid: [
        re.compile(rf"(?im)^\s*(?:Soal|Jawaban|Soal\s*No\.?|No\.?)\s*{re.escape(sid)}\b"),
        re.compile(rf"(?im)^\s*{re.escape(sid)}[\.\)]\s"),
        re.compile(rf"(?im)\bSoal\s*{re.escape(sid)}\b"),
        # Fallback paling longgar — hanya match jika di awal baris dengan spasi
        re.compile(rf"(?m)^\s*{re.escape(sid)}\s"),
    ]
    for sid in SOAL_IDS
}

FASE_ANCHOR = re.compile(
    r"(?im)^\s*FASE\s*(?P<n>\d)\s*[—–-]?\s*(?P<nama>[A-Z][^\n]*)?"
)


def _find_first_anchor(text: str, soal_id: str) -> int | None:
    """Cari posisi pertama anchor untuk soal_id. Return None jika tidak ada."""
    for pat in ANCHOR_PATTERNS[soal_id]:
        m = pat.search(text)
        if m:
            return m.start()
    return None


def _word_count(text: str) -> int:
    return len(re.findall(r"\S+", text))


def segment_answers(
    ingest: IngestResult,
    *,
    strip_soal_text: bool = True,
) -> dict[str, SoalAnswer]:
    """Return dict {soal_id: SoalAnswer}.

    Jika suatu soal tidak ditemukan anchor-nya, SoalAnswer.raw_text akan
    kosong dan kosong=True (di scorer).
    """
    full_text = ingest.full_text

    # Cari offset tiap anchor dalam full_text (ordered by appearance)
    anchors: list[tuple[int, str]] = []
    for sid in SOAL_IDS:
        pos = _find_first_anchor(full_text, sid)
        if pos is not None:
            anchors.append((pos, sid))
    anchors.sort(key=lambda x: x[0])

    # Build answer text per soal = dari anchor sampai anchor berikutnya
    answers: dict[str, SoalAnswer] = {}
    for i, (start, sid) in enumerate(anchors):
        end = anchors[i + 1][0] if i + 1 < len(anchors) else len(full_text)
        chunk = full_text[start:end]
        if strip_soal_text:
            # Hapus baris pertama (anchor itu sendiri) supaya hanya jawaban
            chunk = re.sub(r"^[^\n]*\n?", "", chunk, count=1)
        chunk = chunk.strip()
        answers[sid] = SoalAnswer(
            soal_id=sid,
            raw_text=chunk,
            word_count=_word_count(chunk),
        )

    # Soal yang nggak ketemu anchor-nya → kosong
    for sid in SOAL_IDS:
        if sid not in answers:
            answers[sid] = SoalAnswer(soal_id=sid, raw_text="", word_count=0)

    # --- Map gambar ke soal berdasarkan halaman ---
    # Heuristik: untuk setiap halaman, cari anchor soal YANG MUNCUL DI
    # HALAMAN ITU. Screenshot biasanya ditaruh di halaman yang sama dengan
    # teks soalnya, setelah paragraf prompt/evaluasinya.
    #
    # Algoritma:
    #   1. Hitung anchor yang muncul di tiap halaman (berdasarkan teks halaman).
    #   2. Untuk image di page P:
    #      - Kalau di page P ada anchor soal, ambil anchor TERAKHIR di page itu.
    #      - Kalau tidak, ambil anchor terakhir dari page sebelumnya (yang masih aktif).
    last_anchor_per_page: dict[int, str] = {}
    active_soal: str | None = None
    for p in ingest.pages:
        page_anchors: list[tuple[int, str]] = []
        for sid in SOAL_IDS:
            for pat in ANCHOR_PATTERNS[sid]:
                m = pat.search(p.text)
                if m:
                    page_anchors.append((m.start(), sid))
                    break
        page_anchors.sort(key=lambda x: x[0])
        if page_anchors:
            active_soal = page_anchors[-1][1]
        if active_soal is not None:
            last_anchor_per_page[p.page] = active_soal

    for img in ingest.images:
        matched = last_anchor_per_page.get(img.page)
        if matched is not None:
            img.soal_id = matched

    # --- Re-assignment berdasarkan template UTS ---
    # Template UTS hanya punya 2 slot screenshot: Soal 2.2 (V1) dan Soal 2.3 (V2),
    # diisi berurutan. Karena deteksi per-halaman sering tertukar saat anchor 2.3
    # muncul di halaman yang sama dengan screenshot 2.2, kita override dengan
    # aturan ordering: image pertama → 2.2, image kedua → 2.3.
    sorted_imgs = sorted(ingest.images, key=lambda i: (i.page, i.index_in_page))
    if len(sorted_imgs) >= 1:
        sorted_imgs[0].soal_id = "2.2"
    if len(sorted_imgs) >= 2:
        sorted_imgs[1].soal_id = "2.3"
    # Image ke-3+ tetap di soal hasil deteksi halaman (mungkin bukan screenshot).

    # Reset & re-fill answers[*].images sesuai assignment final
    for sid in SOAL_IDS:
        answers[sid].images.clear()
    for img in sorted_imgs:
        if img.soal_id and img.soal_id in answers:
            answers[img.soal_id].images.append(img)

    return answers


def debug_segmentation(ingest: IngestResult) -> dict[str, int]:
    """Return peta soal_id → offset anchor (buat debug segmentasi)."""
    text = ingest.full_text
    return {sid: _find_first_anchor(text, sid) or -1 for sid in SOAL_IDS}
