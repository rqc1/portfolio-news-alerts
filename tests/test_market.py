"""Tests para el módulo market – MarketService (yfinance)."""

import pytest
from unittest.mock import patch, MagicMock

from modules.market.service import MarketService, AssetLookup, PriceSnapshot


class TestAssetLookup:
    def test_model_fields(self):
        lookup = AssetLookup(
            ticker="AAPL",
            name="Apple Inc.",
            sector="Technology",
            industry="Consumer Electronics",
            country="United States",
            currency="USD",
            market_cap=3_000_000_000_000,
            exchange="NMS",
        )
        assert lookup.ticker == "AAPL"
        assert lookup.sector == "Technology"
        assert lookup.market_cap == 3_000_000_000_000
        assert lookup.aliases == []

    def test_model_defaults(self):
        lookup = AssetLookup(ticker="TEST")
        assert lookup.name == ""
        assert lookup.isin is None
        assert lookup.description == ""


class TestPriceSnapshot:
    def test_model_fields(self):
        snap = PriceSnapshot(ticker="AAPL", price=175.50, currency="USD", change_pct=1.25)
        assert snap.price == 175.50
        assert snap.change_pct == 1.25


class TestMarketServiceLookup:
    @patch("modules.market.service.yf.Ticker")
    def test_lookup_valid_ticker(self, mock_ticker_cls):
        mock_t = MagicMock()
        mock_t.info = {
            "longName": "Apple Inc.",
            "shortName": "Apple Inc.",
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "country": "United States",
            "currency": "USD",
            "marketCap": 3_000_000_000_000,
            "exchange": "NMS",
            "longBusinessSummary": "Apple designs, manufactures...",
        }
        mock_t.isin = "US0378331005"
        mock_ticker_cls.return_value = mock_t

        result = MarketService.lookup_ticker("AAPL")

        assert result is not None
        assert result.ticker == "AAPL"
        assert result.name == "Apple Inc."
        assert result.sector == "Technology"
        assert result.country == "United States"
        assert result.isin == "US0378331005"

    @patch("modules.market.service.yf.Ticker")
    def test_lookup_unknown_ticker(self, mock_ticker_cls):
        mock_t = MagicMock()
        mock_t.info = {}
        mock_ticker_cls.return_value = mock_t

        result = MarketService.lookup_ticker("ZZZZZZZ")
        assert result is None

    @patch("modules.market.service.yf.Ticker")
    def test_lookup_exception(self, mock_ticker_cls):
        mock_ticker_cls.side_effect = Exception("Network error")

        result = MarketService.lookup_ticker("AAPL")
        assert result is None

    @patch("modules.market.service.yf.Ticker")
    def test_lookup_strips_and_uppercases(self, mock_ticker_cls):
        mock_t = MagicMock()
        mock_t.info = {"longName": "Test Corp", "sector": "Tech"}
        mock_t.isin = None
        mock_ticker_cls.return_value = mock_t

        result = MarketService.lookup_ticker("  aapl  ")
        mock_ticker_cls.assert_called_with("AAPL")
        assert result is not None
        assert result.ticker == "AAPL"


class TestMarketServicePrice:
    @patch("modules.market.service.yf.Ticker")
    def test_get_price_valid(self, mock_ticker_cls):
        mock_t = MagicMock()
        mock_t.info = {
            "currentPrice": 175.50,
            "previousClose": 173.00,
            "currency": "USD",
            "dayHigh": 176.00,
            "dayLow": 174.00,
            "volume": 50_000_000,
        }
        mock_ticker_cls.return_value = mock_t

        result = MarketService.get_price("AAPL")
        assert result is not None
        assert result.price == 175.50
        assert result.change_pct == pytest.approx(1.45, abs=0.01)
        assert result.currency == "USD"

    @patch("modules.market.service.yf.Ticker")
    def test_get_price_no_price(self, mock_ticker_cls):
        mock_t = MagicMock()
        mock_t.info = {}
        mock_ticker_cls.return_value = mock_t

        result = MarketService.get_price("ZZZZZ")
        assert result is None

    @patch("modules.market.service.yf.Ticker")
    def test_get_price_zero_prev_close(self, mock_ticker_cls):
        mock_t = MagicMock()
        mock_t.info = {"currentPrice": 10.0, "previousClose": 0, "currency": "EUR"}
        mock_ticker_cls.return_value = mock_t

        result = MarketService.get_price("TEST")
        assert result is not None
        assert result.change_pct == 0.0


class TestMarketServiceBatch:
    @patch("modules.market.service.MarketService.get_price")
    def test_batch_returns_dict(self, mock_get_price):
        snap = PriceSnapshot(ticker="AAPL", price=175.0, currency="USD", change_pct=0.5)
        mock_get_price.side_effect = lambda s: snap if s.upper() == "AAPL" else None

        result = MarketService.get_prices_batch(["AAPL", "INVALID"])
        assert "AAPL" in result
        assert "INVALID" not in result
