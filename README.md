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

PBA Grader mendukung beberapa provider LLM (OpenAI-compatible). Pilih salah satu:

### Opsi 1 — Groq Cloud (default)

```bash
export GROQ_API_KEY="gsk_..."
# PBA_PROVIDER=groq adalah default, tidak perlu di-set.
```

### Opsi 2 — SwiftRouter (OpenAI-compatible router)

```bash
export PBA_PROVIDER=swiftrouter
export SWIFTROUTER_API_KEY="sk-..."
# Default model (sudah optimal untuk rubric grading bilingual):
# export PBA_MODEL_TEXT="gpt-oss-120b"          # reasoning, $0.04/$0.19 per 1M
# export PBA_MODEL_REASONING="gpt-oss-120b"
# export PBA_MODEL_VISION="llama-4-scout"       # vision, $0.08/$0.30 per 1M
```

Estimasi biaya batch 66 mahasiswa via SwiftRouter dengan default di atas: ≈ $0.40 (full mode) atau ≈ $0.10 (mode hemat).

### Opsi 3 — B.AI (OpenAI-compatible, alternatif SwiftRouter)

```bash
export PBA_PROVIDER=bai
export BAI_API_KEY="sk-..."
# Default model (verified end-to-end, nggak butuh deposit/top-up tier premium):
# export PBA_MODEL_TEXT="gpt-5.4-mini"          # $0.75/$4.50 per 1M, multimodal
# export PBA_MODEL_REASONING="gpt-5.4-mini"
# export PBA_MODEL_VISION="gemini-3-flash"      # $0.50/$3.00 per 1M, multimodal
```

Endpoint: `https://api.b.ai/v1`. Auth: `Authorization: Bearer sk-...`. Daftar model lengkap di https://docs.b.ai/llmservice/models/.

Estimasi biaya batch 66 mahasiswa via B.AI dengan default di atas: ≈ **$1.50–3** (full mode dengan self-consistency 3×).

**Upgrade ke Claude (kualitas reasoning lebih tinggi, butuh deposit/top-up b.ai):**

```bash
export PBA_MODEL_TEXT="claude-sonnet-4.5"       # $3.30/$16.50 per 1M
export PBA_MODEL_REASONING="claude-sonnet-4.5"
export PBA_MODEL_VISION="claude-haiku-4.5"      # $1.10/$5.50 per 1M
# Estimasi: ~$8–12 untuk batch 66 mahasiswa.
```

Catatan: model Anthropic di b.ai (Claude Opus/Sonnet/Haiku) terkunci di balik deposit minimum (HTTP 403 `access_denied: Deposit required to unlock premium models` kalau belum top-up). Model OpenAI/Google/MiniMax/GLM bisa langsung dipakai dengan saldo standar.

### Opsi 4 — Endpoint OpenAI-compatible custom

```bash
export PBA_PROVIDER=openai-compat
export PBA_BASE_URL="https://api.example.com/v1"
export PBA_API_KEY="sk-..."
export PBA_MODEL_TEXT="gpt-4o-mini"
export PBA_MODEL_REASONING="gpt-4o"
export PBA_MODEL_VISION="gpt-4o-mini"
```

### Tuning rate limit

Override default throttle/retry kalau provider lu lebih ketat / lebih lega:

```bash
export PBA_THROTTLE_S=2.0       # jeda minimum antar call (default 1.2s)
export PBA_MAX_RETRIES=8        # retry budget per call (default 8)
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
│   ├── grade.py         — LLM-as-judge (provider-agnostic)
│   ├── llm_client.py    — provider routing (Groq/SwiftRouter/B.AI/OpenAI) + throttle+retry
│   ├── vision.py        — grade screenshot 2.2/2.3
│   ├── plagiarism.py    — similarity antar mahasiswa
│   ├── report.py        — Excel rekap + PDF feedback
│   └── cli.py           — entry point
├── input/               — PDF mahasiswa
└── output/              — hasil
```
