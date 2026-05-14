"""Tests para módulo Events (classifier)."""

from modules.events.classifier import (
    FinBERTSentiment,
    ZeroShotEventClassifier,
    EventClassificationService,
)


class TestFinBERTSentiment:
    def test_positive_sentiment(self):
        model = FinBERTSentiment()
        result = model.predict("Revenue surged 25% year over year, beating analyst expectations")
        assert result["sentiment"] in ("positive", "negative", "neutral")
        assert 0.0 <= result["confidence"] <= 1.0
        assert "positive" in result["probabilities"]
        # Strong positive text should tend positive
        assert result["sentiment"] == "positive"

    def test_negative_sentiment(self):
        model = FinBERTSentiment()
        result = model.predict("Company faces massive lawsuit, shares plunge 30%")
        assert result["sentiment"] == "negative"
        assert result["confidence"] > 0.5

    def test_neutral_sentiment(self):
        model = FinBERTSentiment()
        result = model.predict("The company released its annual report today")
        # Neutral text can be classified as neutral or slightly positive/negative
        assert result["sentiment"] in ("positive", "negative", "neutral")
        assert 0.0 <= result["confidence"] <= 1.0

    def test_probabilities_sum_to_one(self):
        model = FinBERTSentiment()
        result = model.predict("Apple earnings beat expectations")
        probs = result["probabilities"]
        total = sum(probs.values())
        assert abs(total - 1.0) < 0.01

    def test_truncation(self):
        model = FinBERTSentiment()
        # Very long text should not crash (truncated at 512 tokens)
        long_text = "Stock market rises. " * 500
        result = model.predict(long_text)
        assert result["sentiment"] in ("positive", "negative", "neutral")


class TestZeroShotEventClassifier:
    def test_classify_earnings(self):
        clf = ZeroShotEventClassifier()
        result = clf.classify("Apple reported quarterly earnings of $1.52 per share, beating estimates")
        assert result["event_type"] in (
            "resultados_empresariales", "guidance_profit_warning", "dividendo_recompra", "otro"
        )
        assert 0.0 <= result["confidence"] <= 1.0
        assert "reasoning" in result

    def test_classify_cyber(self):
        clf = ZeroShotEventClassifier()
        result = clf.classify("Major data breach exposes millions of customer records after ransomware attack")
        assert result["event_type"] in ("ciberincidente", "incidencia_operativa", "otro")

    def test_classify_ma(self):
        clf = ZeroShotEventClassifier()
        result = clf.classify("Microsoft announces $68 billion acquisition of Activision Blizzard")
        assert result["event_type"] in ("fusion_adquisicion", "otro")

    def test_fallback_classify(self):
        result = ZeroShotEventClassifier._fallback_classify(
            "CEO resigned after the board decided to appoint new executive director"
        )
        assert result["event_type"] == "cambio_directivo"
        assert result["confidence"] > 0.0

    def test_fallback_no_match(self):
        result = ZeroShotEventClassifier._fallback_classify(
            "the weather is nice today"
        )
        assert result["event_type"] == "otro"
        assert result["confidence"] < 0.2


class TestEventClassificationService:
    def test_classify_combined(self):
        svc = EventClassificationService()
        result = svc.classify("Tesla shares surge 15% after record delivery numbers")
        assert "sentiment" in result
        assert "event_type" in result
        assert "event_confidence" in result
        assert result["sentiment"]["sentiment"] in ("positive", "negative", "neutral")
        assert result["event_type"] in [
            "resultados_empresariales", "guidance_profit_warning", "regulacion",
            "litigio", "fusion_adquisicion", "ciberincidente", "incidencia_operativa",
            "macroeconomia", "cadena_suministro", "cambio_directivo",
            "dividendo_recompra", "otro",
        ]
