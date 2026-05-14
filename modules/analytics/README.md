# Módulo 11 — Analytics (Métricas de Cartera)

## Propósito

Calcula métricas de rendimiento y riesgo para una cartera de inversión combinando
`quantstats` (cálculo de ratios financieros) y `yfinance` (descarga de retornos
históricos). Proporciona un análisis completo que incluye métricas agregadas de
cartera, rendimiento individual por activo, comparación con benchmark y series
temporales para visualización en el dashboard.

## Archivos

| Archivo | Qué contiene |
|---------|-------------|
| `service.py` | `AnalyticsService` — cálculo de métricas con quantstats + yfinance |
| `__init__.py` | Docstring del módulo |

## Modelos de Datos

### `PortfolioMetrics`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `total_return_pct` | `float` | Retorno total acumulado (%) |
| `annualized_return_pct` | `float` | CAGR anualizado (%) |
| `ytd_return_pct` | `float` | Retorno year-to-date (%) |
| `volatility_pct` | `float` | Volatilidad anualizada (%) |
| `sharpe_ratio` | `float` | Ratio de Sharpe (retorno ajustado a riesgo) |
| `sortino_ratio` | `float` | Ratio de Sortino (solo riesgo bajista) |
| `calmar_ratio` | `float` | Ratio de Calmar (CAGR / max drawdown) |
| `max_drawdown_pct` | `float` | Máximo drawdown (%) |
| `var_95_pct` | `float` | Value at Risk al 95% (%) — pérdida máxima esperada diaria |
| `cvar_95_pct` | `float` | Conditional VaR al 95% (%) — pérdida media en cola |
| `best_day_pct` | `float` | Mejor día (%) |
| `worst_day_pct` | `float` | Peor día (%) |
| `win_rate_pct` | `float` | Tasa de días positivos (%) |
| `benchmark_ticker` | `str` | Ticker del benchmark (default `SPY`) |
| `benchmark_return_pct` | `float` | Retorno total del benchmark (%) |
| `alpha_pct` | `float` | Alpha vs benchmark (retorno total - benchmark) |
| `beta` | `float` | Beta vs benchmark (sensibilidad al mercado) |
| `period` | `str` | Periodo analizado (ej: `1y`, `2y`, `ytd`) |
| `data_points` | `int` | Número de días con datos |

### `AssetPerformance`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `ticker` | `str` | Símbolo del activo |
| `name` | `str` | Nombre (si disponible) |
| `weight` | `float` | Peso en cartera (%) |
| `return_pct` | `float` | Retorno del activo (%) |
| `volatility_pct` | `float` | Volatilidad anualizada del activo (%) |
| `sharpe` | `float` | Ratio de Sharpe del activo |
| `contribution_pct` | `float` | Contribución al retorno total de la cartera (%) |

### `PortfolioAnalyticsResult`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `metrics` | `PortfolioMetrics` | Métricas agregadas de la cartera |
| `asset_performance` | `list[AssetPerformance]` | Rendimiento por activo |
| `return_series` | `list[dict]` | Serie `{date, value}` de retorno acumulado (%) para gráficos |

## Componentes: `AnalyticsService`

| Método | Descripción |
|--------|-------------|
| `compute_metrics(tickers, weights, period, benchmark)` | Pipeline completo: normaliza pesos → descarga retornos → calcula todas las métricas → rendimiento por activo → serie temporal |
| `_download_returns(tickers, period)` | Descarga retornos diarios vía `yf.download()`. Maneja MultiIndex para múltiples tickers |
| `_safe_float(val, default)` | Conversión segura a float (maneja NaN, Inf, None) |

### Pipeline de `compute_metrics`

```
Tickers + Weights
       │
       ▼
 Normalizar pesos (Σ=1)
       │
       ▼
 yf.download() — retornos diarios de todos los tickers + benchmark
       │
       ▼
 Filtrar tickers disponibles (puede que no todos existan en Yahoo Finance)
       │
       ▼
 Calcular retornos ponderados de cartera: Σ(retorno_i × peso_i)
       │
       ▼
 quantstats.stats — Sharpe, Sortino, VaR, drawdown, etc.
       │
       ▼
 Comparar con benchmark (alpha, beta via greeks)
       │
       ▼
 Rendimiento individual por activo
       │
       ▼
 Serie acumulada (1 + r).cumprod() - 1 para gráficos
       │
       ▼
 PortfolioAnalyticsResult
```

## Endpoint API

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/api/analytics/{portfolio_id}?period=1y&benchmark=SPY` | Métricas completas de cartera |

## Dependencias

- `quantstats` — cálculo de ratios financieros (Sharpe, Sortino, VaR, drawdown, etc.)
- `yfinance` — descarga de retornos históricos
- `numpy` — operaciones numéricas (pesos, NaN handling)
- `pandas` — series temporales de retornos
- `pydantic` — validación de modelos

## Relación con otros módulos

```
Portfolio ──▸ Analytics  (proporciona tickers y pesos de la cartera)
Market    ──▸ Analytics  (comparte yfinance para datos de precios)
Analytics ──▸ Dashboard  (métricas + series para KPIs y gráficos)
```

## Consideraciones

- La descarga de datos vía `yf.download()` es síncrona y puede tardar 2-5 segundos.
- Si un ticker no existe en Yahoo Finance, se excluye y se recalculan los pesos.
- Los valores NaN/Inf de quantstats se reemplazan por 0.0 vía `_safe_float()`.
- El benchmark por defecto es SPY (S&P 500); configurable por parámetro.
