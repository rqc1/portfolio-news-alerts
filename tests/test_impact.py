"""Tests para módulo Impact (estimator)."""

from modules.impact.estimator import ImpactEstimator, _severity_label


class TestImpactEstimator:
    def test_positive_earnings(self):
        result = ImpactEstimator.estimate(
            sentiment={"sentiment": "positive", "confidence": 0.9},
            event_type="resultados_empresariales",
            event_confidence=0.8,
            relevance_score=0.9,
            matched_assets=["AAPL"],
        )
        assert result["direction"] == "alcista"
        assert 0.0 <= result["severity"] <= 1.0
        assert 0.0 <= result["confidence"] <= 1.0
        assert result["severity_label"] in ("muy_baja", "baja", "media", "alta", "muy_alta")

    def test_negative_cyber(self):
        result = ImpactEstimator.estimate(
            sentiment={"sentiment": "negative", "confidence": 0.95},
            event_type="ciberincidente",
            event_confidence=0.85,
            relevance_score=0.9,
            matched_assets=["AAPL"],
        )
        assert result["direction"] == "bajista"
        # Ciberincidente + negative should be high severity
        assert result["severity"] > 0.5

    def test_neutral_macro(self):
        result = ImpactEstimator.estimate(
            sentiment={"sentiment": "neutral", "confidence": 0.6},
            event_type="macroeconomia",
            event_confidence=0.7,
            relevance_score=0.5,
            matched_assets=[],
        )
        assert result["direction"] in ("alcista", "bajista", "neutral")
        assert 0.0 <= result["severity"] <= 1.0

    def test_multiple_assets_amplify(self):
        result_single = ImpactEstimator.estimate(
            sentiment={"sentiment": "negative", "confidence": 0.8},
            event_type="regulacion",
            event_confidence=0.7,
            relevance_score=0.8,
            matched_assets=["AAPL"],
        )
        result_multi = ImpactEstimator.estimate(
            sentiment={"sentiment": "negative", "confidence": 0.8},
            event_type="regulacion",
            event_confidence=0.7,
            relevance_score=0.8,
            matched_assets=["AAPL", "TSLA", "MSFT"],
        )
        assert result_multi["severity"] >= result_single["severity"]

    def test_low_relevance_reduces_severity(self):
        result_high = ImpactEstimator.estimate(
            sentiment={"sentiment": "negative", "confidence": 0.8},
            event_type="litigio",
            event_confidence=0.8,
            relevance_score=0.9,
            matched_assets=["AAPL"],
        )
        result_low = ImpactEstimator.estimate(
            sentiment={"sentiment": "negative", "confidence": 0.8},
            event_type="litigio",
            event_confidence=0.8,
            relevance_score=0.3,
            matched_assets=["AAPL"],
        )
        assert result_high["severity"] > result_low["severity"]

    def test_severity_capped_at_one(self):
        result = ImpactEstimator.estimate(
            sentiment={"sentiment": "negative", "confidence": 0.99},
            event_type="ciberincidente",
            event_confidence=0.99,
            relevance_score=0.99,
            matched_assets=["A", "B", "C", "D", "E"],
        )
        assert result["severity"] <= 1.0

    def test_result_structure(self):
        result = ImpactEstimator.estimate(
            sentiment={"sentiment": "positive", "confidence": 0.5},
            event_type="otro",
            event_confidence=0.5,
            relevance_score=0.5,
            matched_assets=[],
        )
        assert "direction" in result
        assert "direction_score" in result
        assert "severity" in result
        assert "severity_label" in result
        assert "confidence" in result
        assert "matched_assets" in result


class TestMergeWithLLM:
    def test_merge_without_llm(self):
        deterministic = {
            "direction": "bajista",
            "direction_score": -0.5,
            "severity": 0.7,
            "severity_label": "alta",
            "confidence": 0.8,
            "matched_assets": ["AAPL"],
        }
        result = ImpactEstimator.merge_with_llm(deterministic, None)
        assert result == deterministic

    def test_merge_with_llm(self):
        deterministic = {
            "direction": "bajista",
            "direction_score": -0.5,
            "severity": 0.7,
            "severity_label": "alta",
            "confidence": 0.8,
            "matched_assets": ["AAPL"],
        }
        llm = {
            "direction": "alcista",
            "severity": 0.3,
            "confidence": 0.9,
        }
        result = ImpactEstimator.merge_with_llm(deterministic, llm)
        # Dirección: el LLM tiene confianza alta (0.9 >= 0.6) -> se acepta.
        assert result["direction"] == "alcista"
        # Severidad: clamp a ±0.2 del ancla determinista (0.7) -> mínimo 0.5.
        assert result["severity"] == 0.5
        assert result["llm_severity_raw"] == 0.3
        # Confianza: media de determinista y LLM (no sobrescritura).
        assert result["confidence"] == 0.85
        # Mantener direction_score determinista como referencia.
        assert result["direction_score"] == -0.5
        assert result["llm_enhanced"] is True

    def test_merge_llm_low_confidence_keeps_deterministic_direction(self):
        deterministic = {
            "direction": "bajista",
            "direction_score": -0.5,
            "severity": 0.7,
            "severity_label": "alta",
            "confidence": 0.8,
            "matched_assets": ["AAPL"],
        }
        llm = {"direction": "alcista", "severity": 0.65, "confidence": 0.4}
        result = ImpactEstimator.merge_with_llm(deterministic, llm)
        # Confianza LLM baja (0.4 < 0.6) y discrepa -> prevalece determinista.
        assert result["direction"] == "bajista"
        # Severidad LLM dentro de la banda -> se respeta.
        assert result["severity"] == 0.65

    def test_merge_llm_severity_clamped_upward(self):
        deterministic = {
            "direction": "alcista",
            "direction_score": 0.5,
            "severity": 0.4,
            "severity_label": "media",
            "confidence": 0.7,
            "matched_assets": ["AAPL"],
        }
        llm = {"direction": "alcista", "severity": 0.95, "confidence": 0.8}
        result = ImpactEstimator.merge_with_llm(deterministic, llm)
        # Clamp superior a 0.4 + 0.2 = 0.6.
        assert result["severity"] == 0.6


class TestSeverityLabel:
    def test_labels(self):
        assert _severity_label(0.9) == "muy_alta"
        assert _severity_label(0.7) == "alta"
        assert _severity_label(0.5) == "media"
        assert _severity_label(0.3) == "baja"
        assert _severity_label(0.1) == "muy_baja"

    def test_boundaries(self):
        assert _severity_label(0.8) == "muy_alta"
        assert _severity_label(0.6) == "alta"
        assert _severity_label(0.4) == "media"
        assert _severity_label(0.2) == "baja"
        assert _severity_label(0.0) == "muy_baja"
