"""Tests para módulo Relevance (service)."""

from modules.relevance.service import RuleBasedRelevance, RelevanceService


class TestRuleBasedRelevance:
    def test_direct_ticker_match(self, sample_portfolio):
        result = RuleBasedRelevance.compute(
            text_lower="apple inc shares surge after aapl earnings beat expectations",
            org_names=[],
            portfolio=sample_portfolio,
        )
        assert "AAPL" in result["matched_assets"]
        assert result["direct_score"] >= 0.9

    def test_name_match(self, sample_portfolio):
        result = RuleBasedRelevance.compute(
            text_lower="tesla announced new factory expansion plans",
            org_names=[],
            portfolio=sample_portfolio,
        )
        assert "TSLA" in result["matched_assets"]
        assert result["direct_score"] >= 0.9

    def test_alias_match(self, sample_portfolio):
        result = RuleBasedRelevance.compute(
            text_lower="santander bank reported quarterly profits above expectations",
            org_names=[],
            portfolio=sample_portfolio,
        )
        assert "SAN.MC" in result["matched_assets"]

    def test_ner_org_match(self, sample_portfolio):
        result = RuleBasedRelevance.compute(
            text_lower="the company reported strong growth",
            org_names=["Apple Inc."],
            portfolio=sample_portfolio,
        )
        assert "AAPL" in result["matched_assets"]
        assert result["direct_score"] >= 0.8

    def test_sector_match(self, sample_portfolio):
        result = RuleBasedRelevance.compute(
            text_lower="the technology sector faces new regulatory challenges",
            org_names=[],
            portfolio=sample_portfolio,
        )
        assert result["sector_match"] is True
        assert result["direct_score"] >= 0.5

    def test_no_match(self, sample_portfolio):
        result = RuleBasedRelevance.compute(
            text_lower="new species of deep sea fish discovered in the pacific ocean",
            org_names=[],
            portfolio=sample_portfolio,
        )
        assert result["matched_assets"] == []
        assert result["direct_score"] == 0.0


class TestRelevanceService:
    def test_high_relevance_direct_match(self, sample_portfolio):
        svc = RelevanceService()
        result = svc.compute_relevance(
            cleaned_text="Apple Inc reported record quarterly revenue driven by iPhone sales",
            org_names=["Apple Inc."],
            portfolio=sample_portfolio,
        )
        assert result["relevance_score"] > 0.5
        assert "AAPL" in result["matched_assets"]

    def test_low_relevance_unrelated(self, sample_portfolio):
        svc = RelevanceService()
        result = svc.compute_relevance(
            cleaned_text="Scientists discover high-temperature superconducting material in laboratory",
            org_names=[],
            portfolio=sample_portfolio,
        )
        assert result["relevance_score"] < 0.5
        assert result["matched_assets"] == []

    def test_result_structure(self, sample_portfolio):
        svc = RelevanceService()
        result = svc.compute_relevance(
            cleaned_text="test news article",
            org_names=[],
            portfolio=sample_portfolio,
        )
        assert "relevance_score" in result
        assert "matched_assets" in result
        assert "direct_score" in result
        assert "semantic_score" in result
        assert 0.0 <= result["relevance_score"] <= 1.0
