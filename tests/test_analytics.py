"""Tests para el módulo analytics – AnalyticsService (quantstats)."""

import numpy as np
import pandas as pd
import pytest
from unittest.mock import patch, MagicMock

from modules.analytics.service import (
    AnalyticsService,
    PortfolioMetrics,
    AssetPerformance,
    PortfolioAnalyticsResult,
)


class TestModels:
    def test_portfolio_metrics_defaults(self):
        m = PortfolioMetrics()
        assert m.sharpe_ratio == 0.0
        assert m.benchmark_ticker == "SPY"
        assert m.period == "1y"

    def test_asset_performance(self):
        a = AssetPerformance(ticker="AAPL", weight=50.0, return_pct=12.5)
        assert a.ticker == "AAPL"
        assert a.weight == 50.0

    def test_result_model(self):
        r = PortfolioAnalyticsResult(metrics=PortfolioMetrics())
        assert r.asset_performance == []
        assert r.return_series == []


class TestSafeFloat:
    def test_normal(self):
        assert AnalyticsService._safe_float(1.5) == 1.5

    def test_nan(self):
        assert AnalyticsService._safe_float(float("nan")) == 0.0

    def test_inf(self):
        assert AnalyticsService._safe_float(float("inf")) == 0.0

    def test_none(self):
        assert AnalyticsService._safe_float(None) == 0.0

    def test_string(self):
        assert AnalyticsService._safe_float("bad") == 0.0

    def test_custom_default(self):
        assert AnalyticsService._safe_float(None, -1.0) == -1.0


class TestComputeMetrics:
    def test_empty_tickers(self):
        assert AnalyticsService.compute_metrics([], []) is None

    def test_zero_weights(self):
        assert AnalyticsService.compute_metrics(["AAPL"], [0.0]) is None

    @patch("modules.analytics.service.AnalyticsService._download_returns")
    def test_no_data(self, mock_dl):
        mock_dl.return_value = None
        result = AnalyticsService.compute_metrics(["AAPL"], [1.0])
        assert result is None

    @patch("modules.analytics.service.AnalyticsService._download_returns")
    def test_valid_single_asset(self, mock_dl):
        dates = pd.date_range("2024-01-02", periods=252, freq="B")
        np.random.seed(42)
        returns = pd.DataFrame(
            {"AAPL": np.random.normal(0.0005, 0.015, 252), "SPY": np.random.normal(0.0003, 0.01, 252)},
            index=dates,
        )
        mock_dl.return_value = returns

        result = AnalyticsService.compute_metrics(["AAPL"], [1.0])
        assert result is not None
        assert isinstance(result.metrics, PortfolioMetrics)
        assert result.metrics.data_points == 252
        assert len(result.asset_performance) == 1
        assert result.asset_performance[0].ticker == "AAPL"
        assert len(result.return_series) > 0

    @patch("modules.analytics.service.AnalyticsService._download_returns")
    def test_multi_asset(self, mock_dl):
        dates = pd.date_range("2024-01-02", periods=100, freq="B")
        np.random.seed(42)
        returns = pd.DataFrame(
            {
                "AAPL": np.random.normal(0.001, 0.015, 100),
                "MSFT": np.random.normal(0.0008, 0.012, 100),
                "SPY": np.random.normal(0.0003, 0.01, 100),
            },
            index=dates,
        )
        mock_dl.return_value = returns

        result = AnalyticsService.compute_metrics(["AAPL", "MSFT"], [0.6, 0.4])
        assert result is not None
        assert len(result.asset_performance) == 2
        weights = [a.weight for a in result.asset_performance]
        assert sum(weights) == pytest.approx(100.0, abs=0.5)

    @patch("modules.analytics.service.AnalyticsService._download_returns")
    def test_ticker_not_in_data(self, mock_dl):
        dates = pd.date_range("2024-01-02", periods=50, freq="B")
        np.random.seed(42)
        returns = pd.DataFrame(
            {"SPY": np.random.normal(0.0003, 0.01, 50)},
            index=dates,
        )
        mock_dl.return_value = returns

        result = AnalyticsService.compute_metrics(["INVALID"], [1.0])
        assert result is None
