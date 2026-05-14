"""Tests para módulo Alerts (deduplication, explainer, engine)."""

from unittest.mock import AsyncMock, patch

import numpy as np

from modules.alerts.deduplication import SemanticDeduplicator, cosine_sim
from modules.alerts.explainer import AlertExplainer


class TestCosineSim:
    def test_identical_vectors(self):
        v = np.array([1.0, 2.0, 3.0])
        assert abs(cosine_sim(v, v) - 1.0) < 0.001

    def test_orthogonal_vectors(self):
        a = np.array([1.0, 0.0])
        b = np.array([0.0, 1.0])
        assert abs(cosine_sim(a, b)) < 0.001

    def test_opposite_vectors(self):
        a = np.array([1.0, 0.0])
        b = np.array([-1.0, 0.0])
        assert abs(cosine_sim(a, b) - (-1.0)) < 0.001

    def test_zero_vector(self):
        a = np.array([1.0, 2.0])
        b = np.array([0.0, 0.0])
        assert cosine_sim(a, b) == 0.0


def _patch_db(dedup):
    """Patch DB methods so tests don't need MongoDB."""
    dedup._check_db = AsyncMock(return_value=0.0)
    dedup._store_in_db = AsyncMock()
    return dedup


class TestSemanticDeduplicator:
    async def test_not_duplicate_first_entry(self):
        dedup = _patch_db(SemanticDeduplicator())
        is_dup, sim = await dedup.is_duplicate("Apple reports record earnings", "id1")
        assert is_dup is False
        assert sim == 0.0

    async def test_duplicate_detection(self):
        dedup = _patch_db(SemanticDeduplicator())
        await dedup.is_duplicate("Apple reports record quarterly earnings for Q4", "id1")
        # Very similar text should be detected as duplicate
        is_dup, sim = await dedup.is_duplicate("Apple posts record quarterly earnings in Q4", "id2")
        assert sim > 0.7  # Should be high similarity

    async def test_different_topics_not_duplicate(self):
        dedup = _patch_db(SemanticDeduplicator())
        await dedup.is_duplicate("Apple reports record quarterly earnings", "id1")
        is_dup, sim = await dedup.is_duplicate("NASA launches new Mars exploration rover", "id2")
        assert is_dup is False
        assert sim < 0.5

    async def test_reset(self):
        dedup = _patch_db(SemanticDeduplicator())
        await dedup.is_duplicate("Some text here", "id1")
        assert len(dedup._recent_embeddings) == 1
        dedup.reset()
        assert len(dedup._recent_embeddings) == 0

    async def test_buffer_limit(self):
        dedup = _patch_db(SemanticDeduplicator())
        for i in range(210):
            await dedup.is_duplicate(f"Unique text number {i} about different topic {i*7}", f"id{i}")
        assert len(dedup._recent_embeddings) <= 200


class TestAlertExplainer:
    def test_template_explanation(self):
        result = AlertExplainer.generate(
            title="Apple earnings beat",
            matched_assets=["AAPL"],
            event_type="resultados_empresariales",
            direction="alcista",
            severity_label="alta",
            confidence=0.85,
            relevance_score=0.9,
            source="reuters_business",
            sentiment="positive",
        )
        assert "AAPL" in result
        assert "alcista" in result
        assert "alta" in result
        assert "reuters_business" in result

    def test_llm_explanation(self):
        result = AlertExplainer.generate(
            title="Apple earnings beat",
            matched_assets=["AAPL"],
            event_type="resultados_empresariales",
            direction="alcista",
            severity_label="alta",
            confidence=0.85,
            relevance_score=0.9,
            source="reuters_business",
            sentiment="positive",
            llm_explanation="Los resultados de Apple superan expectativas, impacto positivo en su cartera",
        )
        # Should use LLM explanation
        assert "Los resultados de Apple" in result
        assert "reuters_business" in result
        assert "0.85" in result

    def test_event_type_translation(self):
        assert "Resultados empresariales" == AlertExplainer.EVENT_TYPE_ES["resultados_empresariales"]
        assert "Ciberincidente" == AlertExplainer.EVENT_TYPE_ES["ciberincidente"]

    def test_empty_assets(self):
        result = AlertExplainer.generate(
            title="Macro event",
            matched_assets=[],
            event_type="macroeconomia",
            direction="neutral",
            severity_label="media",
            confidence=0.5,
            relevance_score=0.5,
            source="fed_press",
            sentiment="neutral",
        )
        assert "cartera general" in result
