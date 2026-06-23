"""Tests del motor de event study (modules/backtest/event_study.py)."""

from datetime import date

import numpy as np
import pandas as pd
import pytest

from modules.backtest.event_study import (
    EventStudyConfig,
    EventSpec,
    estimate_market_model,
    run_event_study,
    run_single_event,
)


def _make_series(n=200, beta=1.2, alpha=0.0002, noise=0.002, seed=0):
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2024-01-01", periods=n)
    mkt = pd.Series(rng.normal(0.0003, 0.01, n), index=dates)
    asset = alpha + beta * mkt + pd.Series(rng.normal(0, noise, n), index=dates)
    return dates, mkt, asset


class TestMarketModel:
    def test_recovers_known_parameters(self):
        rng = np.random.default_rng(1)
        x = rng.normal(0, 0.01, 500)
        y = 0.0005 + 1.5 * x + rng.normal(0, 0.001, 500)
        alpha, beta, resid_std, r2 = estimate_market_model(y, x)
        assert beta == pytest.approx(1.5, abs=0.05)
        assert alpha == pytest.approx(0.0005, abs=0.0005)
        assert 0.0 <= r2 <= 1.0
        assert resid_std > 0

    def test_zero_market_variance(self):
        x = np.zeros(50)
        y = np.full(50, 0.01)
        alpha, beta, resid_std, r2 = estimate_market_model(y, x)
        assert beta == 0.0
        assert alpha == pytest.approx(0.01)

    def test_too_few_points(self):
        alpha, beta, resid_std, r2 = estimate_market_model(np.array([0.01]), np.array([0.0]))
        assert (alpha, beta, resid_std, r2) == (0.0, 0.0, 0.0, 0.0)


class TestSingleEvent:
    def test_detects_positive_abnormal_return(self):
        dates, mkt, asset = _make_series(beta=1.3)
        idx = 150
        asset.iloc[idx] += 0.04
        asset.iloc[idx + 1] += 0.02
        ev_date = dates[idx].date()

        cfg = EventStudyConfig(event_windows=((-1, 1), (-1, 3)))
        res = run_single_event(
            "TEST", ev_date, provider=None, config=cfg,
            predicted_direction="alcista",
            asset_returns=asset, benchmark_returns=mkt,
        )
        assert res.ok
        assert res.beta == pytest.approx(1.3, abs=0.2)
        car = res.car((-1, 1))
        assert car is not None and car > 0.03
        assert res.windows["-1_1"].significant_5pct

    def test_detects_negative_abnormal_return(self):
        dates, mkt, asset = _make_series(beta=1.0)
        idx = 150
        asset.iloc[idx] -= 0.05
        ev_date = dates[idx].date()
        cfg = EventStudyConfig(event_windows=((-1, 1),))
        res = run_single_event(
            "TEST", ev_date, provider=None, config=cfg,
            predicted_direction="bajista",
            asset_returns=asset, benchmark_returns=mkt,
        )
        assert res.ok
        assert res.car((-1, 1)) < 0

    def test_insufficient_estimation_window(self):
        dates, mkt, asset = _make_series(n=40)
        ev_date = dates[5].date()
        cfg = EventStudyConfig(min_estimation_days=30)
        res = run_single_event(
            "TEST", ev_date, provider=None, config=cfg,
            asset_returns=asset, benchmark_returns=mkt,
        )
        assert not res.ok
        assert res.error is not None

    def test_no_data(self):
        res = run_single_event(
            "TEST", date(2024, 6, 1), provider=None,
            asset_returns=pd.Series(dtype="float64"),
            benchmark_returns=pd.Series(dtype="float64"),
        )
        assert not res.ok
        assert res.error == "no_asset_data"


class TestAggregate:
    def test_directional_hit_rate(self):
        # Proveedor sintético que reutiliza las mismas series para todos.
        dates, mkt, asset = _make_series(beta=1.1)
        idx = 150
        asset.iloc[idx] += 0.05
        ev_date = dates[idx].date()

        class FakeProvider:
            def get_returns(self, ticker, start, end):
                return mkt if ticker == "SPY" else asset

        cfg = EventStudyConfig(event_windows=((-1, 1),))
        out = run_event_study(
            [EventSpec("TEST", ev_date, "alcista")],
            provider=FakeProvider(),
            config=cfg,
        )
        assert out["summary"]["n_valid"] == 1
        agg = out["aggregate"]["-1_1"]
        assert agg["directional_hit_rate"] == 1.0
        assert agg["mean_car"] > 0

    def test_serializable(self):
        dates, mkt, asset = _make_series()
        ev_date = dates[150].date()

        class FakeProvider:
            def get_returns(self, ticker, start, end):
                return mkt if ticker == "SPY" else asset

        out = run_event_study([EventSpec("TEST", ev_date, "neutral")], provider=FakeProvider())
        import json
        json.dumps(out)  # no debe lanzar
