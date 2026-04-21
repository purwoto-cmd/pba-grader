"""Buat PDF contoh jawaban mahasiswa buat testing pipeline."""

from __future__ import annotations

import io
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image as RLImage,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)

OUT_DIR = Path(__file__).parent
OUT_DIR.mkdir(exist_ok=True)


def _fake_screenshot(path: Path, title: str, body_lines: list[str]):
    """Buat gambar palsu yang menyerupai screenshot ChatGPT output."""
    W, H = 900, 600
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    try:
        font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
        font_body = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
    except OSError:
        font_title = ImageFont.load_default()
        font_body = ImageFont.load_default()
    # Header bar
    draw.rectangle([0, 0, W, 50], fill="#10a37f")
    draw.text((15, 12), "ChatGPT", fill="white", font=font_title)
    # Title
    draw.text((30, 70), title, fill="black", font=font_title)
    y = 110
    for line in body_lines:
        draw.text((30, y), line, fill="black", font=font_body)
        y += 22
    img.save(path)


def make_student_pdf(out: Path, versi: str, nama: str, nim: str):
    styles = getSampleStyleSheet()
    body = styles["BodyText"]
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], spaceAfter=6)
    doc = SimpleDocTemplate(str(out), pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm)

    story = []
    story.append(Paragraph("JAWABAN UTS — Artificial Intelligence dalam Pendidikan Bahasa Arab", styles["Heading1"]))
    story.append(
        Paragraph(f"Nama Mahasiswa: {nama}<br/>NIM: {nim}<br/>Versi: {versi}", body)
    )
    story.append(Spacer(1, 12))

    if versi == "D":
        # ---- Fase 1 ----
        story.append(Paragraph("Soal 1.1 — Identifikasi Masalah Linguistik", h2))
        story.append(
            Paragraph(
                """Masalah pertama terdapat pada glosarium 'البائع' yang diterjemahkan sebagai 'the seller'.
                Ini tidak konsisten karena entri lain menggunakan bahasa Indonesia, padahal seharusnya 'penjual'.
                Kedua, 'الطماطم' diterjemahkan 'buah tomat merah segar' — terlalu deskriptif, cukup ditulis 'tomat' saja
                sebagai entri glosarium. Ketiga, 'الكيلوغرام' diterjemahkan 'satuan berat internasional' yang merupakan
                definisi ensiklopedis, bukan terjemahan. Seharusnya cukup 'kilogram'. Ini menjadi masalah dalam konteks
                pembelajaran karena glosarium yang tidak konsisten membingungkan siswa kelas VIII MTs dalam memahami
                kosakata baru secara efektif.""",
                body,
            )
        )

        story.append(Paragraph("Soal 1.2 — Identifikasi Masalah Pedagogis", h2))
        story.append(
            Paragraph(
                """Pertama, soal latihan nomor 3 meminta siswa menerjemahkan paragraf dan menjelaskan makna setiap
                kata — ini HOTS tanpa scaffolding untuk level MTs, beban kognitifnya terlalu berat. Kedua, soal nomor 5
                meminta bercerita 10 kalimat dalam bahasa Arab, padahal seluruh komponen ini adalah Qira'ah (membaca),
                jadi maharah yang diuji tidak konsisten. Ketiga, distribusi soal tidak seimbang: 4 soal pilihan ganda
                sangat mudah dicampur dengan 2 soal esai sangat berat, tanpa gradasi wajar. Prinsip scaffolding dan
                progresi LOTS→HOTS dilanggar.""",
                body,
            )
        )

        story.append(Paragraph("Soal 1.3 — Analisis Prompt Asli", h2))
        story.append(
            Paragraph(
                """Clarity: kata 'materi' ambigu — bisa lesson plan, worksheet, teks bacaan, dll. 'Lengkap sama
                latihannya' juga tidak jelas maharah apa yang dilatih. Context: tidak ada info kelas spesifik (VII/VIII/IX),
                kurikulum (K13/Merdeka), atau kompetensi dasar yang ingin dicapai. Specificity: tidak ada spesifikasi
                jumlah soal, panjang teks, level kosakata target, dan standar bahasa (MSA vs dialek). Constraint:
                tidak ada batasan format output, teknik prompting yang dipakai zero-shot asal-asalan tanpa role prompting
                atau contoh few-shot.""",
                body,
            )
        )

        story.append(Paragraph("Soal 2.1 — Pilihan Komponen & Alasan", h2))
        story.append(
            Paragraph(
                """Saya memilih [X] Komponen C: Soal Latihan Pemahaman untuk di-redesign.
                Alasannya karena komponen ini paling banyak bermasalah pedagogis (dari temuan 1.2): distribusi soal
                tidak seimbang, soal nomor 3 dan 5 salah maharah, dan tidak ada gradasi LOTS-HOTS yang wajar.
                Memperbaiki komponen ini akan berdampak paling besar pada kualitas evaluasi pembelajaran.""",
                body,
            )
        )

        story.append(Paragraph("Soal 2.2 — Prompt Versi 1", h2))
        story.append(
            Paragraph(
                """<b>Prompt Versi 1:</b><br/>
                "Role: Anda adalah dosen bahasa Arab berpengalaman yang menyusun evaluasi pembelajaran Qira'ah untuk siswa MTs kelas VIII.
                Konteks: Berdasarkan teks bacaan 'في السوق' (belanja di pasar) untuk siswa MTs kelas VIII dengan kemampuan menengah
                menggunakan Kurikulum Merdeka, KD 3.3 tentang pemahaman teks deskriptif. Spesifikasi: Buat 8 butir soal
                pemahaman Qira'ah dengan gradasi 4 soal LOTS (C1-C2, pilihan ganda) dan 4 soal HOTS (C3-C4, uraian singkat).
                Teknik: few-shot prompting — saya berikan 2 contoh soal yang baik sebagai referensi. Constraint: kosakata hanya
                menggunakan 50 kata paling umum di tema pasar, tiap soal maksimal 2 kalimat, bahasa Arab MSA standar."
                <br/><br/>(Screenshot output terlampir di halaman berikutnya)""",
                body,
            )
        )
        screenshot_v1 = OUT_DIR / "sample_ss_v1.png"
        _fake_screenshot(
            screenshot_v1,
            "Output ChatGPT - Prompt Versi 1",
            [
                "السؤال 1: إلى أين ذهب أحمد؟",
                "  أ) إلى السوق   ب) إلى المسجد",
                "السؤال 2: ماذا اشترى أحمد؟",
                "...",
                "Penjelasan: Soal ini fokus pada pemahaman literal (C1-C2)",
                "sesuai dengan gradasi LOTS yang diminta.",
            ],
        )
        story.append(RLImage(str(screenshot_v1), width=14 * cm, height=9 * cm))

        story.append(Paragraph("Soal 2.3 — Iterasi Prompt V2 & Perbandingan", h2))
        story.append(
            Paragraph(
                """a. Evaluasi Output V1: Output sudah cukup baik untuk LOTS, tapi soal HOTS-nya masih terlalu
                generik dan tidak cukup spesifik ke konteks pasar. Perlu ditambah rubrik penilaian untuk soal uraian.<br/><br/>
                b. Prompt V2: (perubahan yang gue tandai dengan [NEW])
                "Role: Anda dosen bahasa Arab + [NEW] tambahan peran sebagai assessment expert.
                Konteks: sama seperti V1, + [NEW] level Bloom's taxonomy untuk tiap soal wajib dicantumkan.
                Spesifikasi: 8 soal + [NEW] sertakan rubrik penilaian 3-level untuk tiap soal HOTS.
                Teknik: Chain-of-Thought + few-shot. Constraint: tambahkan [NEW] panjang maksimum jawaban mahasiswa 40 kata.
                Alasan perubahan: rubrik eksplisit membuat soal lebih fair dan konteks-pasar lebih terasa."<br/><br/>
                c. (Screenshot V2 terlampir di halaman berikutnya)<br/><br/>
                d. Perbandingan V1 vs V2: Output V2 jauh lebih baik — soal HOTS-nya sekarang punya rubrik penilaian 3-level
                yang eksplisit, dan level Bloom per soal jelas. V1 soal HOTS-nya masih abstrak, V2 terikat konteks
                konkret tawar-menawar di pasar.""",
                body,
            )
        )
        screenshot_v2 = OUT_DIR / "sample_ss_v2.png"
        _fake_screenshot(
            screenshot_v2,
            "Output ChatGPT - Prompt Versi 2 (dengan CoT)",
            [
                "السؤال 1 (Bloom: C2 - Understanding):",
                "  ما هو السعر النهائي للطماطم بعد المساومة؟",
                "Rubrik: skor 3 jika jawaban tepat + kutip teks; skor 2 jika...",
                "Reasoning (CoT): soal ini menguji pemahaman angka dalam dialog...",
            ],
        )
        story.append(RLImage(str(screenshot_v2), width=14 * cm, height=9 * cm))

        story.append(Paragraph("Soal 3.1 — Refleksi Kritis", h2))
        reflection = (
            "Setelah menjalani proses audit dan redesign ini, saya menyadari AI sangat membantu "
            "dalam menghasilkan draft awal bahan ajar bahasa Arab — terutama untuk menyusun kosakata, "
            "dialog singkat, dan soal-soal rutin yang membutuhkan banyak variasi. AI mampu menghasilkan "
            "output dalam hitungan detik, yang kalau dibuat manual bisa memakan waktu berjam-jam. "
            "Namun AI gagal atau butuh koreksi manusia di beberapa titik krusial: ketepatan linguistik "
            "(pemilihan terjemahan yang tidak konsisten), ketepatan pedagogis (distribusi LOTS/HOTS yang "
            "tidak seimbang), dan kesesuaian konteks budaya (contoh percakapan yang tidak natural). "
            "Kemampuan mengaudit output AI menjadi sangat penting bagi guru bahasa Arab karena AI bukan "
            "pengganti keahlian pedagogis, melainkan asisten yang tetap membutuhkan kurator ahli. "
            "Guru yang tidak mampu mengkritisi output AI akan mewariskan kesalahan linguistik dan "
            "pedagogis ke siswa dan merusak kualitas pembelajaran. Pelajaran paling penting: prompt "
            "engineering yang baik (role, context, specificity, constraint) dapat meningkatkan kualitas "
            "output secara dramatis, tapi verifikasi manusia tetap wajib terutama untuk materi bahasa "
            "yang spesifik secara kultural dan linguistik seperti bahasa Arab."
        )
        story.append(Paragraph(reflection, body))

        story.append(Paragraph("Soal 3.2 — Pertanyaan Konseptual", h2))
        story.append(
            Paragraph(
                """a. Chain-of-Thought prompting adalah teknik meminta AI untuk menunjukkan langkah-langkah
                penalarannya secara eksplisit sebelum memberi jawaban akhir. Contoh untuk tata bahasa Arab:
                daripada langsung tanya 'apa mudhari' kata كتب?', kita prompt 'Jelaskan langkah demi langkah:
                (1) tentukan akar, (2) cek pola wazn-nya, (3) terapkan pola mudhari' ke akar tsb.'<br/><br/>
                b. LLM umum (ChatGPT, Claude, Gemini) dilatih multibahasa masif — bagus untuk MSA dan tugas
                kreatif, tapi kurang akurat untuk morfologi Arab dalam atau dialek spesifik. Model khusus Arab
                (AraBERT, Jais, AceGPT) dilatih pada korpus Arab — lebih akurat untuk analisis linguistik dan
                tugas NLP teknis. Pakai LLM umum untuk bikin konten pembelajaran; pakai model khusus Arab
                untuk analisis/koreksi teks Arab.""",
                body,
            )
        )

    doc.build(story)


if __name__ == "__main__":
    make_student_pdf(
        OUT_DIR / "sample_student_D.pdf",
        versi="D",
        nama="Ahmad Fauzan",
        nim="1234567890",
    )
    print(f"Wrote {OUT_DIR / 'sample_student_D.pdf'}")
