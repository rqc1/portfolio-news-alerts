"""
Módulo de validación financiera – Event Study (CAR).

Implementa un estudio de eventos clásico (market model) para medir si las
alertas del sistema anticipan movimientos anormales de precio reales.

Metodología (MacKinlay, 1997; Campbell, Lo y MacKinlay, 1997):

  1. Ventana de estimación (por defecto [-120, -11] días de cotización antes
     del evento): se estima el modelo de mercado por MCO
        R_it = alpha_i + beta_i · R_mt + eps_it
     donde R_it es el retorno diario del activo y R_mt el del índice de
     referencia (benchmark).

  2. Ventana de evento (p.ej. [-1, +1], [-1, +3], [-1, +5]): se calcula el
     retorno anormal
        AR_it = R_it − (alpha_i + beta_i · R_mt)
     y el retorno anormal acumulado
        CAR_i = Σ AR_it.

  3. Significatividad: se contrasta CAR frente a cero usando la desviación
     típica de los residuos de la ventana de estimación (t-stat por evento)
     y un t-test transversal sobre el conjunto de eventos.

  4. Acierto direccional: se compara el signo del CAR realizado con la
     dirección predicha por la alerta (alcista / bajista / neutral).

El proveedor de precios (`PriceProvider`) está desacoplado para permitir
ejecutar el estudio con datos reales (yfinance) o con series sintéticas en
los tests, sin dependencia de red.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Optional, Protocol, Sequence

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class EventStudyConfig:
    """Parámetros del estudio de eventos."""

    benchmark: str = "SPY"
    # Ventana de estimación en días de cotización relativos al evento (t=0).
    estimation_start: int = -120
    estimation_end: int = -11
    # Ventanas de evento [inicio, fin] inclusivas en días de cotización.
    event_windows: tuple[tuple[int, int], ...] = ((-1, 1), (-1, 3), (-1, 5))
    # Mínimo de observaciones válidas en la ventana de estimación.
    min_estimation_days: int = 30
    # Umbral (en proporción, p.ej. 0.005 = 0.5%) para considerar "neutral"
    # un CAR a efectos de acierto direccional.
    neutral_band: float = 0.005

    @property
    def max_window_end(self) -> int:
        return max(end for _, end in self.event_windows)

    @property
    def min_window_start(self) -> int:
        return min(start for start, _ in self.event_windows)


# ---------------------------------------------------------------------------
# Proveedor de precios (desacoplado de yfinance para testabilidad)
# ---------------------------------------------------------------------------
class PriceProvider(Protocol):
    """Devuelve retornos diarios simples indexados por fecha (tz-naive)."""

    def get_returns(self, ticker: str, start: date, end: date) -> pd.Series: ...


class YFinancePriceProvider:
    """Proveedor de retornos basado en yfinance con caché en memoria."""

    def __init__(self) -> None:
        self._cache: dict[tuple[str, date, date], pd.Series] = {}

    def get_returns(self, ticker: str, start: date, end: date) -> pd.Series:
        key = (ticker.upper(), start, end)
        if key in self._cache:
            return self._cache[key]

        import yfinance as yf

        df = yf.Ticker(ticker).history(
            start=start.isoformat(),
            end=(end + timedelta(days=1)).isoformat(),
            auto_adjust=True,
        )
        if df is None or df.empty:
            series = pd.Series(dtype="float64")
        else:
            close = df["Close"].copy()
            close.index = pd.DatetimeIndex(close.index).tz_localize(None).normalize()
            series = close.pct_change().dropna()
        self._cache[key] = series
        return series


# ---------------------------------------------------------------------------
# Estructuras de resultado
# ---------------------------------------------------------------------------
@dataclass
class WindowResult:
    window: tuple[int, int]
    car: float
    t_stat: float
    significant_5pct: bool


@dataclass
class EventResult:
    ticker: str
    event_date: date
    predicted_direction: Optional[str] = None
    alpha: float = 0.0
    beta: float = 0.0
    r2: float = 0.0
    resid_std: float = 0.0
    n_estimation: int = 0
    windows: dict[str, WindowResult] = field(default_factory=dict)
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.error is None and bool(self.windows)

    def car(self, window: tuple[int, int]) -> Optional[float]:
        w = self.windows.get(_window_key(window))
        return None if w is None else w.car

    def to_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "event_date": self.event_date.isoformat(),
            "predicted_direction": self.predicted_direction,
            "alpha": round(self.alpha, 6),
            "beta": round(self.beta, 4),
            "r2": round(self.r2, 4),
            "resid_std": round(self.resid_std, 6),
            "n_estimation": self.n_estimation,
            "windows": {
                k: {
                    "window": list(w.window),
                    "car": round(w.car, 6),
                    "t_stat": round(w.t_stat, 4),
                    "significant_5pct": w.significant_5pct,
                }
                for k, w in self.windows.items()
            },
            "error": self.error,
        }


@dataclass
class AggregateWindowStats:
    window: tuple[int, int]
    n: int
    mean_car: float
    std_car: float
    t_stat: float
    positive_rate: float
    mean_abs_car: float
    directional_hit_rate: Optional[float] = None
    n_directional: int = 0

    def to_dict(self) -> dict:
        return {
            "window": list(self.window),
            "n": self.n,
            "mean_car": round(self.mean_car, 6),
            "std_car": round(self.std_car, 6),
            "t_stat": round(self.t_stat, 4),
            "positive_rate": round(self.positive_rate, 4),
            "mean_abs_car": round(self.mean_abs_car, 6),
            "directional_hit_rate": (
                None if self.directional_hit_rate is None
                else round(self.directional_hit_rate, 4)
            ),
            "n_directional": self.n_directional,
        }


# ---------------------------------------------------------------------------
# Cálculo del modelo de mercado
# ---------------------------------------------------------------------------
def estimate_market_model(
    asset_returns: np.ndarray,
    market_returns: np.ndarray,
) -> tuple[float, float, float, float]:
    """MCO de R_asset sobre R_market.

    Devuelve (alpha, beta, resid_std, r2). `resid_std` es la desviación
    típica de los residuos (con corrección por grados de libertad).
    """
    x = np.asarray(market_returns, dtype="float64")
    y = np.asarray(asset_returns, dtype="float64")
    n = len(x)
    if n < 2:
        return 0.0, 0.0, 0.0, 0.0

    x_mean = x.mean()
    y_mean = y.mean()
    var_x = np.sum((x - x_mean) ** 2)
    if var_x == 0:
        # Sin variación en el mercado: beta=0, alpha=media del activo.
        resid = y - y_mean
        dof = max(n - 2, 1)
        return float(y_mean), 0.0, float(np.sqrt(np.sum(resid**2) / dof)), 0.0

    beta = float(np.sum((x - x_mean) * (y - y_mean)) / var_x)
    alpha = float(y_mean - beta * x_mean)

    y_hat = alpha + beta * x
    resid = y - y_hat
    ss_res = float(np.sum(resid**2))
    ss_tot = float(np.sum((y - y_mean) ** 2))
    dof = max(n - 2, 1)
    resid_std = float(np.sqrt(ss_res / dof))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    return alpha, beta, resid_std, r2


def _window_key(window: tuple[int, int]) -> str:
    return f"{window[0]}_{window[1]}"


# ---------------------------------------------------------------------------
# Estudio de un único evento
# ---------------------------------------------------------------------------
def run_single_event(
    ticker: str,
    event_date: date,
    provider: PriceProvider,
    config: EventStudyConfig = EventStudyConfig(),
    predicted_direction: Optional[str] = None,
    *,
    benchmark_returns: Optional[pd.Series] = None,
    asset_returns: Optional[pd.Series] = None,
) -> EventResult:
    """Calcula el CAR de un evento aplicando el modelo de mercado.

    Si se pasan `asset_returns`/`benchmark_returns` se usan directamente
    (útil para tests); en caso contrario se obtienen del `provider`.
    """
    if isinstance(event_date, datetime):
        event_date = event_date.date()

    result = EventResult(
        ticker=ticker.upper(),
        event_date=event_date,
        predicted_direction=predicted_direction,
    )

    # Rango de calendario suficiente para cubrir estimación + evento.
    lookback_days = abs(config.estimation_start) * 2 + 15
    lookahead_days = config.max_window_end * 2 + 15
    start = event_date - timedelta(days=lookback_days)
    end = event_date + timedelta(days=lookahead_days)

    try:
        if asset_returns is None:
            asset_returns = provider.get_returns(ticker, start, end)
        if benchmark_returns is None:
            benchmark_returns = provider.get_returns(config.benchmark, start, end)
    except Exception as exc:  # pragma: no cover - error de red
        result.error = f"price_fetch_error: {exc}"
        return result

    if asset_returns is None or asset_returns.empty:
        result.error = "no_asset_data"
        return result
    if benchmark_returns is None or benchmark_returns.empty:
        result.error = "no_benchmark_data"
        return result

    # Alinear por fecha.
    aligned = pd.concat(
        {"asset": asset_returns, "mkt": benchmark_returns}, axis=1
    ).dropna()
    aligned = aligned.sort_index()
    if aligned.empty:
        result.error = "no_overlapping_dates"
        return result

    # Localizar t=0: primer día de cotización en o después del event_date.
    event_ts = pd.Timestamp(event_date)
    idx = aligned.index
    pos_array = np.where(idx >= event_ts)[0]
    if len(pos_array) == 0:
        result.error = "event_after_data"
        return result
    t0 = int(pos_array[0])

    # Ventana de estimación.
    est_lo = t0 + config.estimation_start
    est_hi = t0 + config.estimation_end
    if est_lo < 0:
        est_lo = 0
    if est_hi <= est_lo:
        result.error = "insufficient_estimation_window"
        return result

    est = aligned.iloc[est_lo : est_hi + 1]
    if len(est) < config.min_estimation_days:
        result.error = f"too_few_estimation_days({len(est)})"
        return result

    alpha, beta, resid_std, r2 = estimate_market_model(
        est["asset"].to_numpy(), est["mkt"].to_numpy()
    )
    result.alpha = alpha
    result.beta = beta
    result.r2 = r2
    result.resid_std = resid_std
    result.n_estimation = len(est)

    if resid_std == 0:
        result.error = "zero_residual_std"
        return result

    # Calcular CAR por ventana.
    for window in config.event_windows:
        w_lo = t0 + window[0]
        w_hi = t0 + window[1]
        if w_lo < 0 or w_hi >= len(aligned):
            # Datos insuficientes para esta ventana concreta.
            continue
        seg = aligned.iloc[w_lo : w_hi + 1]
        ar = seg["asset"].to_numpy() - (alpha + beta * seg["mkt"].to_numpy())
        car = float(np.sum(ar))
        n_days = len(ar)
        # t-stat del CAR: CAR / (resid_std · sqrt(L)).
        se_car = resid_std * np.sqrt(n_days)
        t_stat = car / se_car if se_car > 0 else 0.0
        result.windows[_window_key(window)] = WindowResult(
            window=window,
            car=car,
            t_stat=float(t_stat),
            significant_5pct=bool(abs(t_stat) > 1.96),
        )

    if not result.windows:
        result.error = "no_event_window_data"

    return result


# ---------------------------------------------------------------------------
# Estudio agregado sobre un conjunto de eventos
# ---------------------------------------------------------------------------
@dataclass
class EventSpec:
    ticker: str
    event_date: date
    predicted_direction: Optional[str] = None


def run_event_study(
    events: Sequence[EventSpec],
    provider: Optional[PriceProvider] = None,
    config: EventStudyConfig = EventStudyConfig(),
) -> dict:
    """Ejecuta el estudio sobre múltiples eventos y agrega resultados.

    Devuelve un dict serializable con:
      - per_event: lista de resultados individuales
      - aggregate: estadísticos por ventana (mean CAR, t-stat transversal,
        positive rate, directional hit-rate)
      - summary: conteos de eventos válidos / descartados
    """
    if provider is None:
        provider = YFinancePriceProvider()

    per_event: list[EventResult] = []
    for spec in events:
        res = run_single_event(
            ticker=spec.ticker,
            event_date=spec.event_date,
            provider=provider,
            config=config,
            predicted_direction=spec.predicted_direction,
        )
        per_event.append(res)

    valid = [e for e in per_event if e.ok]
    aggregate = _aggregate_events(valid, config)

    errors: dict[str, int] = {}
    for e in per_event:
        if e.error:
            key = e.error.split("(")[0].split(":")[0]
            errors[key] = errors.get(key, 0) + 1

    return {
        "config": {
            "benchmark": config.benchmark,
            "estimation_window": [config.estimation_start, config.estimation_end],
            "event_windows": [list(w) for w in config.event_windows],
            "neutral_band": config.neutral_band,
        },
        "summary": {
            "n_events": len(per_event),
            "n_valid": len(valid),
            "n_discarded": len(per_event) - len(valid),
            "errors": errors,
        },
        "aggregate": {k: v.to_dict() for k, v in aggregate.items()},
        "per_event": [e.to_dict() for e in per_event],
    }


def _aggregate_events(
    events: list[EventResult],
    config: EventStudyConfig,
) -> dict[str, AggregateWindowStats]:
    from scipy import stats as scipy_stats

    out: dict[str, AggregateWindowStats] = {}
    for window in config.event_windows:
        key = _window_key(window)
        cars = [e.car(window) for e in events if e.car(window) is not None]
        cars = [c for c in cars if c is not None]
        if not cars:
            continue
        arr = np.asarray(cars, dtype="float64")
        n = len(arr)
        mean_car = float(arr.mean())
        std_car = float(arr.std(ddof=1)) if n > 1 else 0.0
        if std_car > 0 and n > 1:
            t_stat = float(mean_car / (std_car / np.sqrt(n)))
        else:
            t_stat = 0.0
        positive_rate = float(np.mean(arr > 0))
        mean_abs_car = float(np.mean(np.abs(arr)))

        # Acierto direccional: solo sobre eventos con dirección predicha.
        hits = 0
        n_dir = 0
        for e in events:
            car = e.car(window)
            if car is None or not e.predicted_direction:
                continue
            pred = e.predicted_direction
            if pred == "neutral":
                if abs(car) <= config.neutral_band:
                    hits += 1
                n_dir += 1
            elif pred in ("alcista", "bajista"):
                realized = (
                    "alcista" if car > config.neutral_band
                    else "bajista" if car < -config.neutral_band
                    else "neutral"
                )
                if realized == pred:
                    hits += 1
                n_dir += 1
        hit_rate = (hits / n_dir) if n_dir else None

        out[key] = AggregateWindowStats(
            window=window,
            n=n,
            mean_car=mean_car,
            std_car=std_car,
            t_stat=t_stat,
            positive_rate=positive_rate,
            mean_abs_car=mean_abs_car,
            directional_hit_rate=hit_rate,
            n_directional=n_dir,
        )
        _ = scipy_stats  # disponible para extensiones (e.g. test no paramétrico)
    return out
