"""Deteksi kemiripan antar jawaban mahasiswa (indikasi plagiarisme/jawaban AI yang sama)."""

from __future__ import annotations

import logging
from itertools import combinations
from pathlib import Path

import numpy as np

from .schema import PlagiarismFlag, StudentResult

log = logging.getLogger(__name__)

# Threshold cosine similarity di atas mana dianggap suspicious
SIMILARITY_THRESHOLD = 0.85

# Soal yang paling rentan identik (Fase 2 prompt + Fase 3 refleksi)
SOAL_CHECK = ["2.2", "2.3", "3.1", "3.2"]

_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
_model = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(_MODEL_NAME)
    return _model


def detect_plagiarism(
    results: list[StudentResult],
    *,
    threshold: float = SIMILARITY_THRESHOLD,
    soal_ids: list[str] | None = None,
) -> list[PlagiarismFlag]:
    """Return list pasangan (PDF_a, PDF_b, soal_id) dengan cosine similarity > threshold."""
    if len(results) < 2:
        return []
    soal_ids = soal_ids or SOAL_CHECK
    model = _get_model()
    flags: list[PlagiarismFlag] = []

    for sid in soal_ids:
        texts = []
        owners: list[Path] = []
        for r in results:
            ans = r.answers.get(sid)
            if ans and len(ans.raw_text) > 50:
                texts.append(ans.raw_text)
                owners.append(r.pdf_path)
        if len(texts) < 2:
            continue
        embs = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        sims = np.matmul(embs, embs.T)
        for i, j in combinations(range(len(texts)), 2):
            s = float(sims[i, j])
            if s >= threshold:
                flags.append(
                    PlagiarismFlag(
                        pdf_a=owners[i],
                        pdf_b=owners[j],
                        soal_id=sid,
                        cosine_similarity=s,
                    )
                )
    return sorted(flags, key=lambda f: -f.cosine_similarity)
