#!/usr/bin/env bash
# Auto-setup untuk GitHub Codespaces / devcontainer lokal.
set -euo pipefail

echo "==> Install Tesseract OCR + language packs (ara, ind, eng)…"
sudo apt-get update -qq
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
  tesseract-ocr \
  tesseract-ocr-ara \
  tesseract-ocr-ind \
  tesseract-ocr-eng \
  poppler-utils
sudo rm -rf /var/lib/apt/lists/*

echo "==> Install Python dependencies via pip (editable)…"
pip install --upgrade pip
pip install -e .

echo "==> Siapkan folder kerja…"
mkdir -p input output/feedback output/images

cat <<'BANNER'

===========================================================
  PBA Grader siap dipakai di Codespace ini.

  1. Set GROQ_API_KEY sebagai Codespace secret:
     https://github.com/settings/codespaces
     (atau untuk sementara: export GROQ_API_KEY=gsk_xxx)

  2. Upload PDF mahasiswa ke folder input/
     (drag-drop file ke panel Explorer VS Code)

  3. Jalanin:
     pba-grader grade --input input/ --output output/

  4. Hasil di:
     - output/rekap.xlsx            (skor per mahasiswa, overrideable)
     - output/feedback/*.pdf        (feedback per mahasiswa)

  Debug 1 PDF aja:
     pba-grader debug input/namafile.pdf
===========================================================
BANNER
