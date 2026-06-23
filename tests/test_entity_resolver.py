"""Tests del resolver canónico de entidades (modules/nlp/entity_resolver.py)."""

from modules.nlp.entity_resolver import (
    EntityResolver,
    company_root,
    normalize_company_name,
    strip_accents,
)
from modules.portfolio.models import Asset, Portfolio


def _portfolio():
    return Portfolio(
        user_id="u1",
        name="test",
        assets=[
            Asset(ticker="AAPL", name="Apple Inc.", sector="Technology",
                  country="USA", aliases=["Apple Computer"]),
            Asset(ticker="MSFT", name="Microsoft Corporation", sector="Technology",
                  country="USA", aliases=["MSFT", "Microsoft"]),
            Asset(ticker="SAN", name="Banco Santander S.A.", sector="Financials",
                  country="Spain", aliases=["Santander"]),
        ],
    )


class TestNormalization:
    def test_strip_suffixes(self):
        assert normalize_company_name("Apple Inc.") == "apple"
        assert normalize_company_name("Microsoft Corporation") == "microsoft"
        assert normalize_company_name("Banco Santander S.A.") == "banco santander"

    def test_strip_accents(self):
        assert strip_accents("Société Générale") == "Societe Generale"

    def test_company_root(self):
        assert company_root("Apple Inc.") == "apple"
        assert company_root("Banco Santander S.A.") == "banco"

    def test_empty(self):
        assert normalize_company_name("") == ""
        assert company_root("") == ""


class TestResolver:
    def test_resolves_full_name_variants(self):
        r = EntityResolver.from_portfolio(_portfolio())
        assert "AAPL" in r.resolve_tickers("Apple Inc. announced new products")
        assert "AAPL" in r.resolve_tickers("Apple reported strong earnings")
        assert "AAPL" in r.resolve_tickers("apple computer is hiring")

    def test_resolves_ticker(self):
        r = EntityResolver.from_portfolio(_portfolio())
        assert "MSFT" in r.resolve_tickers("MSFT stock jumped today")

    def test_resolves_alias(self):
        r = EntityResolver.from_portfolio(_portfolio())
        assert "SAN" in r.resolve_tickers("Santander raised its dividend")

    def test_suffix_insensitive(self):
        r = EntityResolver.from_portfolio(_portfolio())
        assert "MSFT" in r.resolve_tickers("Microsoft Corp posted results")
        assert "MSFT" in r.resolve_tickers("Microsoft Corporation posted results")

    def test_no_false_positive_substring(self):
        r = EntityResolver.from_portfolio(_portfolio())
        # "pineapple" no debe casar con Apple (límite de palabra para raíz corta
        # no aplica aquí, pero substring de palabra completa sí se exige).
        tickers = r.resolve_tickers("I ate a pineapple yesterday")
        assert "AAPL" not in tickers

    def test_scores_present(self):
        r = EntityResolver.from_portfolio(_portfolio())
        res = r.resolve("Apple Inc. and Microsoft are tech giants")
        tickers = {x["ticker"] for x in res}
        assert {"AAPL", "MSFT"} <= tickers
        assert all(0.0 < x["score"] <= 1.0 for x in res)

    def test_empty_portfolio(self):
        p = Portfolio(user_id="u", name="empty", assets=[])
        r = EntityResolver.from_portfolio(p)
        assert r.resolve_tickers("Apple and Microsoft") == []
