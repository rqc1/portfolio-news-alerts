"""
Deduplicación semántica de alertas.

Dos niveles:
  1. Caché en memoria (rápido, primeras 200 alertas)
  2. MongoDB persistente (sobrevive reinicios, con TTL de 30 días)
"""

import logging
from datetime import datetime, timezone

import numpy as np
from functools import lru_cache
from sentence_transformers import SentenceTransformer

import config
from database.mongodb import MongoDB

logger = logging.getLogger(__name__)


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

    def _check_memory(self, emb: np.ndarray) -> float:
        """Primer nivel: buscar duplicados en caché en memoria."""
        max_sim = 0.0
        for _, prev_emb in self._recent_embeddings:
            sim = cosine_sim(emb, prev_emb)
            if sim > max_sim:
                max_sim = sim
        return max_sim

    async def _check_db(self, emb: np.ndarray) -> float:
        """Segundo nivel: buscar duplicados en MongoDB."""
        try:
            collection = MongoDB.dedup_embeddings()
            cursor = collection.find(
                {},
                {"embedding": 1},
            ).sort("created_at", -1).limit(500)
            docs = await cursor.to_list(length=500)

            max_sim = 0.0
            for doc in docs:
                prev_emb = np.array(doc["embedding"], dtype=np.float32)
                sim = cosine_sim(emb, prev_emb)
                if sim > max_sim:
                    max_sim = sim
            return max_sim
        except Exception:
            logger.debug("Dedup DB check failed, using memory only")
            return 0.0

    async def _store_in_db(self, alert_id: str, emb: np.ndarray) -> None:
        """Persiste el embedding en MongoDB para dedup entre reinicios."""
        try:
            collection = MongoDB.dedup_embeddings()
            await collection.insert_one({
                "alert_id": alert_id,
                "embedding": emb.tolist(),
                "created_at": datetime.now(timezone.utc),
            })
        except Exception:
            logger.debug("Failed to persist dedup embedding")

    async def is_duplicate(self, text: str, alert_id: str = "") -> tuple[bool, float]:
        """
        Comprueba si text es un duplicado de alguna alerta reciente.
        Nivel 1: memoria (rápido). Nivel 2: MongoDB (persistente).
        Returns: (is_dup, max_similarity)
        """
        emb = self.model.encode(text[:512])

        # Nivel 1: memoria
        max_sim = self._check_memory(emb)

        # Nivel 2: MongoDB (solo si no hay match en memoria)
        if max_sim < self.threshold:
            db_sim = await self._check_db(emb)
            max_sim = max(max_sim, db_sim)

        is_dup = max_sim >= self.threshold

        if not is_dup:
            # Guardar en ambos niveles
            self._recent_embeddings.append((alert_id, emb))
            if len(self._recent_embeddings) > 200:
                self._recent_embeddings = self._recent_embeddings[-200:]
            await self._store_in_db(alert_id, emb)

        return is_dup, round(max_sim, 4)

    def reset(self):
        self._recent_embeddings.clear()
