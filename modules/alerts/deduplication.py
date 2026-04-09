"""
Deduplicación semántica de alertas.

Agrupa noticias que describen el mismo evento para evitar alertas redundantes.
"""

import numpy as np
from functools import lru_cache
from sentence_transformers import SentenceTransformer

import config


@lru_cache(maxsize=1)
def _load_model():
    return SentenceTransformer(config.EMBEDDING_MODEL)


def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    dot = np.dot(a, b)
    norm = np.linalg.norm(a) * np.linalg.norm(b)
    if norm == 0:
        return 0.0
    return float(dot / norm)


class SemanticDeduplicator:
    """Detecta si una alerta nueva es semánticamente duplicada respecto a alertas recientes."""

    def __init__(self, threshold: float = config.ALERT_DEDUP_SIMILARITY):
        self.model = _load_model()
        self.threshold = threshold
        self._recent_embeddings: list[tuple[str, np.ndarray]] = []  # (alert_id, embedding)

    def is_duplicate(self, text: str, alert_id: str = "") -> tuple[bool, float]:
        """
        Comprueba si text es un duplicado de alguna alerta reciente.
        Returns: (is_dup, max_similarity)
        """
        emb = self.model.encode(text[:512])

        max_sim = 0.0
        for _, prev_emb in self._recent_embeddings:
            sim = cosine_sim(emb, prev_emb)
            if sim > max_sim:
                max_sim = sim

        is_dup = max_sim >= self.threshold

        if not is_dup:
            self._recent_embeddings.append((alert_id, emb))
            # Mantener las últimas 200 alertas
            if len(self._recent_embeddings) > 200:
                self._recent_embeddings = self._recent_embeddings[-200:]

        return is_dup, round(max_sim, 4)

    def reset(self):
        self._recent_embeddings.clear()
