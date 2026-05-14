"""
Servicio de analytics de cartera – quantstats + yfinance.

Calcula métricas de rendimiento y riesgo para una cartera de inversión:
  - Retorno acumulado, anualizado
  - Sharpe, Sortino, Calmar ratios
  - Máximo drawdown, VaR, CVaR
  - Volatilidad anualizada
  - Comparación con benchmark
"""

import logging
from typing import Optional

import numpy as np
import pandas as pd
import quantstats as qs
import yfinance as yf

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Modelos
# ---------------------------------------------------------------------------
class PortfolioMetrics(BaseModel):
    """Métricas de rendimiento y riesgo de una cartera."""
    # Rendimiento
    total_return_pct: float = 0.0
    annualized_return_pct: float = 0.0
    ytd_return_pct: float = 0.0
    # Riesgo
    volatility_pct: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    max_drawdown_pct: float = 0.0
    var_95_pct: float = 0.0
    cvar_95_pct: float = 0.0
    # Info
    best_day_pct: float = 0.0
    worst_day_pct: float = 0.0
    win_rate_pct: float = 0.0
    # Benchmark
    benchmark_ticker: str = "SPY"
    benchmark_return_pct: float = 0.0
    alpha_pct: float = 0.0
    beta: float = 0.0
    # Meta
    period: str = "1y"
    data_points: int = 0


class AssetPerformance(BaseModel):
    """Rendimiento individual de un activo."""
    ticker: str
    name: str = ""
    weight: float = 0.0
    return_pct: float = 0.0
    volatility_pct: float = 0.0
    sharpe: float = 0.0
    contribution_pct: float = 0.0


class PortfolioAnalyticsResult(BaseModel):
    """Resultado completo del análisis de cartera."""
    metrics: PortfolioMetrics
    asset_performance: list[AssetPerformance] = Field(default_factory=list)
    return_series: list[dict] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Servicio
# ---------------------------------------------------------------------------
class AnalyticsService:
    """Calcula métricas de cartera usando quantstats y yfinance."""

    @staticmethod
    def _download_returns(
        tickers: list[str],
        period: str = "1y",
    ) -> Optional[pd.DataFrame]:
        """Descarga retornos diarios para una lista de tickers."""
        try:
            df = yf.download(
                tickers,
                period=period,
                auto_adjust=True,
                progress=False,
                threads=True,
            )
            if df.empty:
                return None

            # yf.download devuelve MultiIndex si hay varios tickers
            if isinstance(df.columns, pd.MultiIndex):
                closes = df["Close"]
            else:
                closes = df[["Close"]]
                closes.columns = [tickers[0]]

            returns = closes.pct_change().dropna()
            return returns if not returns.empty else None
        except Exception as exc:
            logger.error("Error descargando datos: %s", exc)
            return None

    @staticmethod
    def _safe_float(val, default: float = 0.0) -> float:
        """Convierte a float de forma segura (maneja NaN, Inf)."""
        if val is None:
            return default
        try:
            f = float(val)
            return default if (np.isnan(f) or np.isinf(f)) else round(f, 4)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def compute_metrics(
        tickers: list[str],
        weights: list[float],
        period: str = "1y",
        benchmark: str = "SPY",
    ) -> Optional[PortfolioAnalyticsResult]:
        """Calcula métricas completas de una cartera.

        Args:
            tickers: Lista de tickers de los activos.
            weights: Pesos correspondientes (deben sumar ~1.0).
            period: Periodo de análisis (1y, 2y, 5y, ytd, max).
            benchmark: Ticker del benchmark (default SPY).

        Returns:
            PortfolioAnalyticsResult o None si no hay datos.
        """
        if not tickers or not weights:
            return None

        # Normalizar pesos
        w = np.array(weights, dtype=float)
        w_sum = w.sum()
        if w_sum <= 0:
            return None
        w = w / w_sum

        # Descargar retornos
        all_tickers = list(set(tickers + [benchmark]))
        returns_df = AnalyticsService._download_returns(all_tickers, period)
        if returns_df is None:
            return None

        sf = AnalyticsService._safe_float

        # Retornos de cada activo en cartera
        available_tickers = [t for t in tickers if t in returns_df.columns]
        if not available_tickers:
            return None

        available_weights = np.array(
            [w[i] for i, t in enumerate(tickers) if t in returns_df.columns],
            dtype=float,
        )
        available_weights = available_weights / available_weights.sum()

        portfolio_returns = (
            returns_df[available_tickers] * available_weights
        ).sum(axis=1)

        # Benchmark
        bench_returns = (
            returns_df[benchmark] if benchmark in returns_df.columns else None
        )

        # --- Métricas con quantstats ---
        total_return = sf(qs.stats.comp(portfolio_returns)) * 100
        ann_return = sf(qs.stats.cagr(portfolio_returns)) * 100

        # YTD
        now = pd.Timestamp.now()
        ytd_mask = portfolio_returns.index >= pd.Timestamp(now.year, 1, 1)
        ytd_ret = sf(qs.stats.comp(portfolio_returns[ytd_mask])) * 100 if ytd_mask.any() else 0.0

        volatility = sf(qs.stats.volatility(portfolio_returns)) * 100
        sharpe = sf(qs.stats.sharpe(portfolio_returns))
        sortino = sf(qs.stats.sortino(portfolio_returns))
        calmar = sf(qs.stats.calmar(portfolio_returns))
        max_dd = sf(qs.stats.max_drawdown(portfolio_returns)) * 100
        var_95 = sf(qs.stats.var(portfolio_returns)) * 100
        cvar_95 = sf(qs.stats.cvar(portfolio_returns)) * 100
        best = sf(qs.stats.best(portfolio_returns)) * 100
        worst = sf(qs.stats.worst(portfolio_returns)) * 100
        win_rate = sf(qs.stats.win_rate(portfolio_returns)) * 100

        # Benchmark stats
        bench_total = 0.0
        alpha = 0.0
        beta_val = 0.0
        if bench_returns is not None and not bench_returns.empty:
            bench_total = sf(qs.stats.comp(bench_returns)) * 100
            alpha = total_return - bench_total
            try:
                greeks = qs.stats.greeks(portfolio_returns, bench_returns)
                beta_val = sf(greeks.get("beta", 0.0)) if isinstance(greeks, dict) else 0.0
            except Exception:
                beta_val = 0.0

        metrics = PortfolioMetrics(
            total_return_pct=round(total_return, 2),
            annualized_return_pct=round(ann_return, 2),
            ytd_return_pct=round(ytd_ret, 2),
            volatility_pct=round(volatility, 2),
            sharpe_ratio=round(sharpe, 2),
            sortino_ratio=round(sortino, 2),
            calmar_ratio=round(calmar, 2),
            max_drawdown_pct=round(max_dd, 2),
            var_95_pct=round(var_95, 2),
            cvar_95_pct=round(cvar_95, 2),
            best_day_pct=round(best, 2),
            worst_day_pct=round(worst, 2),
            win_rate_pct=round(win_rate, 2),
            benchmark_ticker=benchmark,
            benchmark_return_pct=round(bench_total, 2),
            alpha_pct=round(alpha, 2),
            beta=round(beta_val, 2),
            period=period,
            data_points=len(portfolio_returns),
        )

        # Rendimiento individual de cada activo
        asset_perf: list[AssetPerformance] = []
        for i, t in enumerate(available_tickers):
            if t not in returns_df.columns:
                continue
            r = returns_df[t]
            a_ret = sf(qs.stats.comp(r)) * 100
            a_vol = sf(qs.stats.volatility(r)) * 100
            a_sharpe = sf(qs.stats.sharpe(r))
            contribution = round(a_ret * float(available_weights[i]) / 100, 2) if total_return != 0 else 0.0
            asset_perf.append(AssetPerformance(
                ticker=t,
                weight=round(float(available_weights[i]) * 100, 1),
                return_pct=round(a_ret, 2),
                volatility_pct=round(a_vol, 2),
                sharpe=round(a_sharpe, 2),
                contribution_pct=round(contribution * 100, 2),
            ))

        # Serie temporal de retornos acumulados para gráfico
        cum_returns = (1 + portfolio_returns).cumprod() - 1
        return_series = [
            {"date": d.strftime("%Y-%m-%d"), "value": round(float(v) * 100, 2)}
            for d, v in cum_returns.items()
        ]

        return PortfolioAnalyticsResult(
            metrics=metrics,
            asset_performance=asset_perf,
            return_series=return_series,
        )
