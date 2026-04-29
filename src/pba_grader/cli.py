"""CLI entry point.

Contoh:
  pba-grader grade --input input/ --output output/
  pba-grader grade --input input/ --output output/ --skip-vision
  pba-grader debug --pdf input/mahasiswa1.pdf
"""

from __future__ import annotations

import logging
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from .detect import detect_identity
from .ingest import ingest_pdf
from .pipeline import grade_batch
from .plagiarism import detect_plagiarism
from .report import write_excel_rekap, write_plagiarism_report
from .schema import SOAL_IDS
from .segment import debug_segmentation, segment_answers

app = typer.Typer(help="Penilaian otomatis UTS AI dalam Pendidikan Bahasa Arab.")
console = Console()

KEYS_DIR = Path(__file__).resolve().parent.parent.parent / "keys"


@app.callback()
def _setup(verbose: bool = typer.Option(False, "--verbose", "-v")):
    logging.basicConfig(
        level=logging.INFO if verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


@app.command()
def grade(
    input_dir: Path = typer.Option(..., "--input", "-i", help="Folder berisi PDF mahasiswa"),
    output_dir: Path = typer.Option(..., "--output", "-o", help="Folder output (rekap + feedback)"),
    rubric: Path = typer.Option(KEYS_DIR / "rubric.yaml", help="Path rubric YAML"),
    key_d: Path = typer.Option(KEYS_DIR / "key_D.md", help="Kunci jawaban referensi Versi D"),
    key_e: Path = typer.Option(KEYS_DIR / "key_E.md", help="Kunci jawaban referensi Versi E"),
    skip_vision: bool = typer.Option(
        False, "--skip-vision", help="Skip grading screenshot (hemat kuota)."
    ),
    skip_plagiarism: bool = typer.Option(
        False, "--skip-plagiarism", help="Skip plagiarism check."
    ),
    no_self_consistency: bool = typer.Option(
        False,
        "--no-self-consistency",
        help="Skip 3x sampling untuk soal bobot >=15% (1 call per soal, lebih hemat kuota).",
    ),
    no_cache: bool = typer.Option(
        False, "--no-cache", help="Abaikan cache (re-grade ulang semua, walaupun ada hasil sebelumnya)."
    ),
    throttle: float = typer.Option(
        1.2,
        "--throttle",
        help="Jeda minimum (detik) antar call Groq API. Naikkan kalau sering 429.",
    ),
    max_retries: int = typer.Option(
        8, "--max-retries", help="Maks retry saat dapat 429/error transient."
    ),
):
    """Grade semua PDF di folder input/."""
    results = grade_batch(
        input_dir,
        output_dir,
        rubric_path=rubric,
        key_d_path=key_d,
        key_e_path=key_e,
        skip_vision=skip_vision,
        enable_self_consistency=not no_self_consistency,
        use_cache=not no_cache,
        throttle_s=throttle,
        max_retries=max_retries,
    )

    # Rekap Excel
    rekap_path = output_dir / "rekap.xlsx"
    write_excel_rekap(results, rekap_path)
    console.print(f"[green]Rekap:[/green] {rekap_path}")

    # Plagiarism
    if not skip_plagiarism:
        flags = detect_plagiarism(results)
        if flags:
            flag_path = output_dir / "flags_plagiarism.xlsx"
            write_plagiarism_report(flags, flag_path)
            console.print(
                f"[yellow]Plagiarism flags:[/yellow] {len(flags)} pasangan → {flag_path}"
            )
        else:
            console.print("[green]Tidak ada kemiripan antar jawaban di atas threshold.[/green]")

    # Ringkas di console
    table = Table(title="Rekap Skor UTS")
    table.add_column("PDF")
    table.add_column("Nama")
    table.add_column("NIM")
    table.add_column("Versi")
    table.add_column("Total", justify="right")
    table.add_column("Level")
    for r in results:
        table.add_row(
            r.pdf_path.name,
            r.identity.nama or "-",
            r.identity.nim or "-",
            r.identity.versi,
            f"{r.total:.2f}",
            r.total_level,
        )
    console.print(table)


@app.command()
def debug(
    pdf: Path = typer.Argument(..., exists=True, readable=True),
    out: Path = typer.Option(Path("output/debug"), "--out", "-o"),
):
    """Debug: tampilkan hasil ingest + segmentasi satu PDF (tanpa grading)."""
    out.mkdir(parents=True, exist_ok=True)
    ingest = ingest_pdf(pdf, image_out_dir=out / pdf.stem)
    identity = detect_identity(ingest)
    answers = segment_answers(ingest)
    seg = debug_segmentation(ingest)

    console.rule(f"Identitas {pdf.name}")
    console.print(identity.model_dump())
    console.rule("Segmentasi (offset anchor tiap soal)")
    console.print(seg)

    console.rule("Cuplikan jawaban per soal")
    for sid in SOAL_IDS:
        ans = answers[sid]
        n_images = len(ans.images)
        preview = ans.raw_text[:300].replace("\n", " ")
        console.print(
            f"[bold]{sid}[/bold] ({ans.word_count} kata, {n_images} img): {preview}…"
        )

    console.rule("Gambar yang diekstrak")
    for img in ingest.images:
        console.print(f"- {img.path.name} (page={img.page}, soal={img.soal_id}, {img.width}x{img.height})")


if __name__ == "__main__":
    app()
