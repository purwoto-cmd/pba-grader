# Kunci Jawaban Referensi — UTS Versi D (Tema: Berbelanja di Pasar)

> Catatan: Kunci ini adalah **referensi**, bukan jawaban tunggal. Dosen dapat menerima jawaban lain yang valid. LLM judge harus memberi kredit untuk temuan lain yang akurat dan beralasan.

## Topik Paket Audit
- Tema: التسوق في السوق (Berbelanja di Pasar)
- Jenjang: Siswa MTs kelas VIII
- Prompt asli mahasiswa: *"buatin materi bahasa arab tema belanja di pasar buat siswa mts lengkap sama latihannya"*

---

## Soal 1.1 — Masalah Linguistik yang Ditanamkan

Berikut masalah linguistik yang sengaja ditanamkan dalam paket audit (mahasiswa boleh mengidentifikasi lainnya yang valid):

1. **Glosarium `البائع`** diterjemahkan `the seller` — campur bahasa Inggris, tidak konsisten dengan entri lain berbahasa Indonesia. Seharusnya `penjual`.
2. **Glosarium `الطماطم`** diterjemahkan `buah tomat merah segar` — terlalu deskriptif, tidak efisien sebagai entri glosarium. Seharusnya cukup `tomat`.
3. **Glosarium `الكيلوغرام`** diterjemahkan `satuan berat internasional` — ini definisi ensiklopedis, bukan terjemahan. Seharusnya `kilogram`.
4. **Glosarium `الثوم`** diterjemahkan `garlic` — bahasa Inggris lagi, tidak konsisten. Seharusnya `bawang putih`.
5. **Glosarium `النكهة`** diterjemahkan `rasa masakan yang lezat dan enak` — berlebihan dan deskriptif. Seharusnya `cita rasa` / `aroma`.
6. **Transliterasi `al-thamathim`** untuk `الطماطم` — tidak tepat, seharusnya `al-thamaathim` (dengan perpanjangan vokal).
7. **Dialog Kalam**: Pembeli menjawab `أريد أن أشتري` (saya ingin membeli) tanpa objek spesifik — tidak natural dan tidak representatif sebagai contoh percakapan tawar-menawar otentik.

---

## Soal 1.2 — Masalah Pedagogis yang Ditanamkan

1. **Soal latihan nomor 3** ("Terjemahkan paragraf kedua... dan jelaskan makna setiap kata") — jauh melampaui tingkat kognitif wajar untuk satu butir soal, tidak sesuai level MTs (HOTS tanpa scaffolding).
2. **Soal latihan nomor 5** ("Ceritakan kembali... minimal 10 kalimat dalam bahasa Arab") — ini soal kalam/berbicara, bukan qira'ah tertulis. Maharah yang diuji tidak konsisten dengan komponen Qira'ah.
3. **Distribusi soal tidak seimbang** — dari 6 soal, nomor 3 dan 5 memerlukan waktu sangat lama (esai panjang), sementara nomor 1, 2, 4, 6 pilihan ganda mudah (LOTS). Tidak ada gradasi wajar.
4. **Dialog kalam tidak memiliki konteks situasi yang jelas** — siswa tidak tahu latar, tujuan, atau peran masing-masing dengan detail. Tidak ada variasi respons.
5. **Instruksi kalam** ("Ganti kata خضروات dengan benda lain") terlalu dangkal sebagai scaffolding — tidak membimbing siswa mengembangkan strategi tawar-menawar otentik.

---

## Soal 1.3 — Analisis Prompt Asli (4 Dimensi)

### Clarity
- Kata `materi` ambigu — bisa teks bacaan, lesson plan, lembar kerja, worksheet, dll.
- `lengkap sama latihannya` tidak jelas: latihan untuk maharah apa? (istima', kalam, qira'ah, kitabah).

### Context
- Tidak ada info level kemahiran siswa MTs (kelas 7/8/9?).
- Tidak ada info kurikulum yang digunakan, jam pelajaran, kompetensi dasar yang dituju.

### Specificity
- Tidak ada spesifikasi jumlah soal, tipe soal, panjang teks.
- Tidak ada spesifikasi level kosakata (kata baru vs kosakata yang diasumsikan sudah dikenal), standar bahasa (MSA/dialek).

### Constraint
- Tidak ada batasan kompleksitas kalimat.
- Tidak ada instruksi format output.
- Tidak ada teknik prompting yang diterapkan (zero-shot asal-asalan tanpa role atau contoh).

---

## Soal 3.2 — Pertanyaan Konseptual Versi D

### 3.2a — Chain-of-Thought (CoT) Prompting

Chain-of-Thought (CoT) adalah teknik prompting di mana AI diminta menunjukkan **langkah penalaran secara bertahap** sebelum memberikan jawaban akhir.

**Contoh penerapan untuk tata bahasa Arab**: Daripada langsung meminta *"Jelaskan tashrif kata كتب"*, dosen memberikan instruksi bertahap: *"Jelaskan langkah demi langkah: (1) tentukan akar katanya, (2) identifikasi polanya (wazn), (3) turunkan setiap bentuknya (madhi, mudhari', amr, dll)."* CoT menghasilkan penjelasan yang lebih terstruktur dan mudah dipahami siswa.

### 3.2b — LLM Umum vs Model Arab Khusus

**Model umum** (ChatGPT, Claude, Gemini) dilatih pada dataset multibahasa masif — unggul untuk tugas kreatif, pemahaman konteks luas, dan instruksi kompleks dalam MSA (Modern Standard Arabic). Namun performanya menurun untuk dialek lokal, terminologi keislaman yang sangat teknis, atau analisis morfologi mendalam.

**Model khusus Arab** (AraBERT untuk klasifikasi/NER, Jais/AceGPT untuk generasi teks Arab) dioptimalkan pada korpus Arab — lebih akurat untuk analisis linguistik Arab, tagging morfologi, dan tugas NLP teknis. Namun kemampuan instruksi dan kreativitasnya lebih terbatas.

**Panduan penggunaan**:
- Gunakan **LLM umum** untuk membuat konten pembelajaran, prompt engineering, dan dialog interaktif.
- Gunakan **model khusus Arab** untuk analisis teks Arab, koreksi gramatikal otomatis, dan tugas NLP berbasis teks Arab.
