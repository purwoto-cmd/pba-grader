# Kunci Jawaban Referensi — UTS Versi E (Tema: Di Bandara)

> Catatan: Kunci ini adalah **referensi**, bukan jawaban tunggal. Dosen dapat menerima jawaban lain yang valid. LLM judge harus memberi kredit untuk temuan lain yang akurat dan beralasan.

## Topik Paket Audit
- Tema: في المطار (Di Bandara)
- Jenjang: Siswa SMA kelas X
- Prompt asli: *"buatkan materi bahasa arab untuk siswa sma tentang percakapan di bandara sama soal soalnya"*

---

## Soal 1.1 — Masalah Linguistik yang Ditanamkan

1. **Glosarium `المسافرون`** diterjemahkan `para traveler` — campur bahasa Inggris, tidak konsisten. Seharusnya `para musafir` / `para penumpang`.
2. **Glosarium `ضواحي`** diterjemahkan `periferal` — terlalu teknis dan bukan padanan natural. Seharusnya `pinggiran kota` / `kawasan suburban`.
3. **Glosarium `عنبر الطائرة`** diterjemahkan `gudang pesawat` — tidak tepat. Yang dimaksud adalah `bagasi kabin` / `bagasi pesawat`, bukan gudang.
4. **Teks paragraf pertama** terlalu panjang dan menggunakan kalimat kompleks bersusun (klausa relatif berganda) — tidak sesuai untuk level pemula-menengah SMA.
5. **Dialog kalam** menggunakan jawaban `أريد أن أذهب إلى مكان` (saya ingin pergi ke suatu tempat) — sangat tidak natural dan tidak memberi contoh bahasa yang otentik.

---

## Soal 1.2 — Masalah Pedagogis yang Ditanamkan

1. **Soal istima' nomor 4 dan 5 bukan soal listening** — nomor 4 adalah essay tentang prosedur imigrasi (tidak dapat dijawab hanya dari audio), nomor 5 adalah soal kosakata hafalan. Tidak sesuai dengan tujuan maharah istima'.
2. **Tidak ada audio yang disediakan** untuk soal istima' — anakronisme antara instruksi ("dengarkan audio") dan kenyataan (tidak ada audio).
3. **Dialog kalam tidak memberi scaffolding** — siswa diminta mempraktikkan dialog tapi tidak diberi petunjuk situasi, tujuan komunikasi, atau variasi respons.
4. **Tidak ada gradasi level** — teks dan soal tidak disesuaikan dengan level tertentu (beginner/intermediate/advanced).
5. **Soal istima' nomor 5** ("sebutkan 10 kosakata") adalah soal menghafal, bukan pemahaman mendengarkan.

---

## Soal 1.3 — Analisis Prompt Asli (4 Dimensi)

### Clarity
- Kata `materi` ambigu — bisa berarti teks, lesson plan, worksheet, dll.

### Context
- Tidak ada informasi level kemahiran siswa SMA.
- Tidak ada info kurikulum yang digunakan, jumlah pertemuan, karakter siswa.

### Specificity
- Tidak ada spesifikasi maharah yang dituju (istima', kalam, qira'ah, kitabah).
- Tidak ada format output, panjang, standar bahasa (MSA/dialek).

### Constraint
- Tidak ada batasan jumlah soal, level kosakata, format penyajian.

### Teknik prompting
- Zero-shot tanpa role, tanpa format output, tanpa contoh — level terendah dalam prompt engineering.

---

## Soal 3.2 — Pertanyaan Konseptual Versi E

### 3.2a — Zero-shot vs Few-shot Prompting

**Zero-shot** adalah teknik di mana AI diminta menyelesaikan tugas **tanpa memberikan contoh** sebelumnya, hanya instruksi. Cocok untuk tugas sederhana yang sudah sering dilatih pada model.

**Few-shot** menyertakan **beberapa contoh** (biasanya 2-5) di dalam prompt sebagai referensi pola sebelum AI menjawab. Lebih cocok untuk tugas spesifik yang memerlukan format konsisten atau gaya tertentu.

**Contoh konteks penggunaan di pembelajaran bahasa Arab**:
- **Zero-shot**: *"Terjemahkan kalimat ini ke bahasa Arab: Saya pergi ke pasar."* — AI bisa langsung menerjemahkan.
- **Few-shot**: *"Ubah kalimat berikut menjadi bentuk mudhari' sesuai pola. Contoh: كتب → يكتب. ذهب → يذهب. شرب → ?"* — memberikan pola/contoh agar output AI konsisten dengan format yang dibutuhkan guru.

### 3.2b — Tantangan Khusus NLP Bahasa Arab

Minimal 2 faktor berikut perlu disebutkan:

1. **Morfologi kompleks (rich morphology)**: Bahasa Arab bersifat fusional dengan sistem akar-pola (root-pattern). Satu kata dapat memiliki banyak bentuk turunan (tashrif), membuat tokenisasi dan lemmatisasi sulit.
2. **Diakritik (harakat) opsional**: Teks Arab modern sering ditulis tanpa tanda baca vokal. Satu rangkaian huruf yang sama dapat dibaca berbeda makna/fungsinya tanpa konteks yang jelas.
3. **Arah penulisan kanan-ke-kiri (RTL)** dan script yang berbeda — menimbulkan masalah teknis pada text processing, rendering, dan pencampuran dengan huruf Latin.
4. **Perbedaan antara MSA (Modern Standard Arabic) dan dialek**: bahasa percakapan sehari-hari (Mesir, Saudi, Syam, Maghreb) berbeda signifikan dari MSA, sehingga model perlu dilatih pada korpus dialek spesifik.
5. **Ketersediaan korpus dan dataset** yang lebih terbatas dibandingkan bahasa Inggris, khususnya untuk domain spesifik (hukum, kedokteran, dll.).
6. **Homograf dan polisemi** yang sangat umum karena banyak kata dengan pola huruf sama memiliki arti berbeda tanpa harakat.
