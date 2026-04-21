"""Ingestion PDF mahasiswa → teks + gambar per halaman.

Strategi:
1. Coba `pdfplumber` untuk ekstrak teks layer asli (cepat, akurat).
2. Kalau teks kurang dari threshold, fallback ke OCR (Tesseract ara+ind) via PyMuPDF render.
3. Ekstrak semua gambar embed (untuk screenshot output AI di soal 2.2/2.3).
"""

from __future__ import annotations

import hashlib
import io
import logging
from pathlib import Path

import fitz  # PyMuPDF
import pdfplumber
import pytesseract
from PIL import Image

from .schema import ExtractedImage, IngestResult, PageText

log = logging.getLogger(__name__)

# Jika teks per halaman kurang dari threshold ini → OCR fallback
OCR_TEXT_THRESHOLD = 40

# Screenshot biasanya lebih besar dari icon/logo — filter ukuran minimum
MIN_IMAGE_WIDTH = 200
MIN_IMAGE_HEIGHT = 120


def ingest_pdf(pdf_path: Path, image_out_dir: Path) -> IngestResult:
    """Ekstrak teks + gambar dari PDF mahasiswa."""
    pdf_path = Path(pdf_path)
    image_out_dir = Path(image_out_dir)
    image_out_dir.mkdir(parents=True, exist_ok=True)

    pages: list[PageText] = []

    # --- Step 1: teks via pdfplumber ---
    with pdfplumber.open(pdf_path) as pdf:
        for idx, page in enumerate(pdf.pages, start=1):
            text = (page.extract_text() or "").strip()
            pages.append(PageText(page=idx, text=text, via_ocr=False))

    # --- Step 2: OCR fallback untuk halaman yang teksnya tipis ---
    doc = fitz.open(pdf_path)
    for page_text in pages:
        if len(page_text.text) >= OCR_TEXT_THRESHOLD:
            continue
        page = doc.load_page(page_text.page - 1)
        # Render ke image resolusi tinggi
        pix = page.get_pixmap(dpi=250)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        try:
            ocr_text = pytesseract.image_to_string(img, lang="ara+ind+eng")
        except pytesseract.TesseractError as exc:
            log.warning("OCR gagal di halaman %d: %s", page_text.page, exc)
            ocr_text = ""
        if len(ocr_text.strip()) > len(page_text.text):
            page_text.text = ocr_text.strip()
            page_text.via_ocr = True

    # --- Step 3: ekstrak gambar (hanya yang berukuran screenshot) ---
    images: list[ExtractedImage] = []
    stem = pdf_path.stem
    for page_idx in range(len(doc)):
        page = doc.load_page(page_idx)
        img_list = page.get_images(full=True)
        for img_idx, img_info in enumerate(img_list):
            xref = img_info[0]
            try:
                base = doc.extract_image(xref)
            except (ValueError, RuntimeError) as exc:
                log.warning("Gagal ekstrak image xref=%d: %s", xref, exc)
                continue
            img_bytes = base["image"]
            ext = base["ext"]
            try:
                pil = Image.open(io.BytesIO(img_bytes))
                w, h = pil.size
            except Exception as exc:  # noqa: BLE001
                log.warning("Gagal parse image xref=%d: %s", xref, exc)
                continue
            if w < MIN_IMAGE_WIDTH or h < MIN_IMAGE_HEIGHT:
                continue
            digest = hashlib.sha1(img_bytes).hexdigest()[:10]
            out_path = image_out_dir / f"{stem}_p{page_idx + 1}_i{img_idx}_{digest}.{ext}"
            out_path.write_bytes(img_bytes)
            images.append(
                ExtractedImage(
                    page=page_idx + 1,
                    index_in_page=img_idx,
                    path=out_path,
                    width=w,
                    height=h,
                )
            )
    doc.close()

    full_text = "\n\n".join(p.text for p in pages)
    return IngestResult(pdf_path=pdf_path, pages=pages, images=images, full_text=full_text)
