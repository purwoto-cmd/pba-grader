"""Orkestrasi: 1 PDF → StudentResult. Dan batch: N PDF → rekap."""

from __future__ import annotations

import logging
import time
from pathlib import Path

from groq import Groq

from .detect import detect_identity
from .grade import Judge
from .ingest import ingest_pdf
from .schema import SOAL_IDS, StudentResult
from .segment import segment_answers
from .vision import VisionGrader

log = logging.getLogger(__name__)

TEMA = {"D": "Berbelanja di Pasar (التسوق في السوق)", "E": "Di Bandara (في المطار)", "UNKNOWN": "(versi tidak terdeteksi)"}


def grade_one_pdf(
    pdf_path: Path,
    image_out_dir: Path,
    judge: Judge,
    vision: VisionGrader | None = None,
    skip_vision: bool = False,
) -> StudentResult:
    t0 = time.time()
    ingest = ingest_pdf(pdf_path, image_out_dir=image_out_dir / pdf_path.stem)
    identity = detect_identity(ingest)
    answers = segment_answers(ingest)

    result = StudentResult(pdf_path=pdf_path, identity=identity, answers=answers)

    # Flag yang nggak butuh LLM
    if identity.versi == "UNKNOWN":
        result.flags.append("Versi UTS tidak terdeteksi — periksa PDF manual")
    if not identity.nim:
        result.flags.append("NIM tidak terdeteksi")
    if not identity.nama:
        result.flags.append("Nama tidak terdeteksi")
    empty_soal = [sid for sid in SOAL_IDS if not answers[sid].raw_text.strip()]
    if empty_soal:
        result.flags.append(f"Jawaban kosong di soal: {', '.join(empty_soal)}")

    # Grade tiap soal
    versi = identity.versi if identity.versi in ("D", "E") else "D"  # fallback
    for sid in SOAL_IDS:
        log.info("  grading %s soal %s…", pdf_path.name, sid)
        try:
            score = judge.grade_soal(sid, answers[sid], versi)
        except Exception as exc:  # noqa: BLE001
            log.exception("Gagal grade soal %s: %s", sid, exc)
            from .schema import SoalScore
            score = SoalScore(
                soal_id=sid,
                bobot=judge.soal_by_id[sid]["bobot"],
                level="kurang",
                skor_0_100=0.0,
                skor_terbobot=0.0,
                feedback=f"[Error saat grading: {exc}]",
            )
            result.flags.append(f"Error grading soal {sid}")
        result.scores[sid] = score

    # Vision grading untuk soal 2.2 dan 2.3
    if vision and not skip_vision:
        for sid in ("2.2", "2.3"):
            imgs = answers[sid].images
            if not imgs:
                if sid in ("2.2", "2.3"):
                    result.flags.append(f"Tidak ada screenshot lampiran di soal {sid}")
                continue
            versi_prompt = "V1" if sid == "2.2" else "V2"
            summary = vision.summarize_for_soal(imgs, tema=TEMA[identity.versi], versi_prompt=versi_prompt)
            # Tempelkan hasil vision ke raw_judge supaya bisa direview
            sc = result.scores[sid]
            sc.raw_judge.setdefault("vision", summary)
            if not summary.get("has_valid_screenshot"):
                sc.feedback = (
                    "[Screenshot terlampir tapi tidak jelas sebagai output AI yang relevan. "
                    "Pertimbangkan untuk turunkan skor jika tidak ada bukti output AI.]\n"
                    + sc.feedback
                )
                result.flags.append(f"Soal {sid}: screenshot tidak valid menurut vision check")

    # Aggregate total
    total = sum(sc.skor_terbobot for sc in result.scores.values())
    result.total = total
    result.total_level = _total_level(total)
    result.elapsed_s = time.time() - t0
    return result


def _total_level(total: float):
    # total sudah dalam skala 0-100 (bobot menjumlah ke 100)
    if total >= 85:
        return "sangat_baik"
    if total >= 70:
        return "baik"
    if total >= 60:
        return "cukup"
    return "kurang"


def grade_batch(
    input_dir: Path,
    output_dir: Path,
    rubric_path: Path,
    key_d_path: Path,
    key_e_path: Path,
    *,
    skip_vision: bool = False,
) -> list[StudentResult]:
    pdfs = sorted(Path(input_dir).glob("*.pdf"))
    log.info("Menemukan %d PDF di %s", len(pdfs), input_dir)

    image_dir = Path(output_dir) / "images"
    feedback_dir = Path(output_dir) / "feedback"
    feedback_dir.mkdir(parents=True, exist_ok=True)

    client = Groq()
    judge = Judge(rubric_path=rubric_path, key_d_path=key_d_path, key_e_path=key_e_path, client=client)
    vision = None if skip_vision else VisionGrader(client=client)

    results: list[StudentResult] = []
    for i, pdf in enumerate(pdfs, start=1):
        log.info("[%d/%d] Grading %s …", i, len(pdfs), pdf.name)
        try:
            result = grade_one_pdf(
                pdf, image_out_dir=image_dir, judge=judge, vision=vision, skip_vision=skip_vision
            )
        except Exception as exc:  # noqa: BLE001
            log.exception("Gagal total grading %s: %s", pdf.name, exc)
            continue
        results.append(result)

        # Tulis feedback PDF per mahasiswa
        try:
            from .report import write_student_feedback_pdf
            write_student_feedback_pdf(result, feedback_dir / f"{pdf.stem}_feedback.pdf")
        except Exception as exc:  # noqa: BLE001
            log.warning("Gagal bikin feedback PDF untuk %s: %s", pdf.name, exc)

    return results
