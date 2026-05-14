"""Tests para módulo Portfolio (models + service)."""

from datetime import datetime, timezone

from modules.portfolio.models import Portfolio, Asset


class TestAsset:
    def test_create_asset(self):
        asset = Asset(ticker="AAPL", name="Apple Inc.")
        assert asset.ticker == "AAPL"
        assert asset.name == "Apple Inc."
        assert asset.weight == 0.0
        assert asset.aliases == []

    def test_asset_with_all_fields(self):
        asset = Asset(
            ticker="SAN.MC",
            name="Banco Santander",
            isin="ES0113900J37",
            sector="Financials",
            industry="Banking",
            country="Spain",
            weight=0.25,
            aliases=["Santander", "BSAN"],
        )
        assert asset.isin == "ES0113900J37"
        assert asset.sector == "Financials"
        assert asset.weight == 0.25
        assert len(asset.aliases) == 2


class TestPortfolio:
    def test_create_portfolio(self, sample_portfolio):
        assert sample_portfolio.user_id == "test_user"
        assert len(sample_portfolio.assets) == 3

    def test_get_tickers(self, sample_portfolio):
        tickers = sample_portfolio.get_tickers()
        assert set(tickers) == {"AAPL", "SAN.MC", "TSLA"}

    def test_get_sectors(self, sample_portfolio):
        sectors = sample_portfolio.get_sectors()
        assert "Technology" in sectors
        assert "Financials" in sectors

    def test_get_countries(self, sample_portfolio):
        countries = sample_portfolio.get_countries()
        assert "US" in countries
        assert "Spain" in countries

    def test_get_all_names(self, sample_portfolio):
        names = sample_portfolio.get_all_names()
        assert "apple inc." in names
        assert "aapl" in names
        assert "apple" in names
        assert "santander" in names

    def test_empty_portfolio(self):
        p = Portfolio(user_id="empty")
        assert p.get_tickers() == []
        assert p.get_sectors() == set()
        assert p.get_countries() == set()
        assert p.get_all_names() == []

    def test_portfolio_has_timestamps(self):
        p = Portfolio(user_id="ts_test")
        assert isinstance(p.created_at, datetime)
        assert isinstance(p.updated_at, datetime)
