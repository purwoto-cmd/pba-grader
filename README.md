# PBA Grader

Alat bantu penilaian otomatis untuk UTS mata kuliah *Artificial Intelligence dalam Pendidikan Bahasa Arab* (Arabic AI Prompt Engineer Track). Sistem ini menilai jawaban mahasiswa berbentuk PDF menggunakan **LLM-as-judge berbasis rubrik** dengan Groq Cloud API.

## Cakupan

Mendukung dua varian soal:

- **Versi D** — tema *Berbelanja di Pasar* (التسوق في السوق)
- **Versi E** — tema *Di Bandara* (في المطار)

Struktur soal identik (3 fase, 8 butir, total 100%). Rubrik dan bobot ada di `keys/rubric.yaml`. Kunci jawaban referensi ada di `keys/key_D.md` dan `keys/key_E.md`.

## Pipeline

```
PDF mahasiswa  →  ingest (teks+gambar)  →  detect identitas & versi
              →  segment per soal       →  LLM judge per soal (Groq)
              →  aggregate & plagiarism →  Excel rekap + PDF feedback
```

## Instalasi

```bash
cd pba-grader
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Sistem butuh Tesseract OCR dengan paket bahasa Arab & Indonesia:

```bash
sudo apt-get install -y tesseract-ocr tesseract-ocr-ara tesseract-ocr-ind
```

## Konfigurasi

Set environment variable:

```bash
export GROQ_API_KEY="gsk_..."
```

## Pemakaian

```bash
# Taruh semua PDF mahasiswa di folder input/
pba-grader grade --input input/ --output output/

# Output:
# output/rekap.xlsx       — satu baris per mahasiswa
# output/feedback/*.pdf   — feedback per mahasiswa
# output/flags.xlsx       — anomali (identitas kosong, duplikat, plagiarisme)
```

## Struktur Project

```
pba-grader/
├── keys/
│   ├── rubric.yaml      — rubrik 8 soal, 4 level, bobot
│   ├── key_D.md         — kunci jawaban referensi versi D
│   └── key_E.md         — kunci jawaban referensi versi E
├── src/pba_grader/
│   ├── ingest.py        — PDF → teks + gambar
│   ├── detect.py        — identitas (nama, NIM) + deteksi versi
│   ├── segment.py       — split jawaban per soal
│   ├── grade.py         — LLM-as-judge (Groq)
│   ├── vision.py        — grade screenshot 2.2/2.3
│   ├── plagiarism.py    — similarity antar mahasiswa
│   ├── report.py        — Excel rekap + PDF feedback
│   └── cli.py           — entry point
├── input/               — PDF mahasiswa
└── output/              — hasil
```
