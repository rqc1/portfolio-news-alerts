# Módulo 10 — Market (Datos de Mercado en Tiempo Real)

## Propósito

Proporciona acceso a datos de mercado financiero mediante la API de Yahoo Finance
a través de `yfinance`. Permite buscar información de activos (auto-fill), obtener
precios actuales con variación diaria, consultar precios en lote y descargar
históricos OHLCV para alimentar el módulo de analytics y enriquecer las
recomendaciones del advisor.

## Archivos

| Archivo | Qué contiene |
|---------|-------------|
| `service.py` | `MarketService` — wrapper estático sobre yfinance |
| `__init__.py` | Docstring del módulo |

## Modelos de Datos

### `AssetLookup`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `ticker` | `str` | Símbolo del activo (ej: `AAPL`) |
| `name` | `str` | Nombre completo (ej: `Apple Inc.`) |
| `sector` | `str` | Sector (ej: `Technology`) |
| `industry` | `str` | Industria (ej: `Consumer Electronics`) |
| `country` | `str` | País de cotización |
| `currency` | `str` | Divisa de cotización |
| `market_cap` | `float?` | Capitalización de mercado |
| `isin` | `str?` | Código ISIN (si disponible) |
| `exchange` | `str` | Bolsa de cotización |
| `description` | `str` | Descripción de la empresa (max 500 chars) |
| `aliases` | `list[str]` | Nombres alternativos (shortName, etc.) |

### `PriceSnapshot`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `ticker` | `str` | Símbolo del activo |
| `price` | `float` | Precio actual |
| `currency` | `str` | Divisa (default `USD`) |
| `change_pct` | `float` | Variación diaria en % |
| `day_high` | `float?` | Máximo del día |
| `day_low` | `float?` | Mínimo del día |
| `volume` | `int?` | Volumen negociado |
| `timestamp` | `datetime` | Momento de la consulta (UTC) |

## Componentes: `MarketService`

| Método | Descripción |
|--------|-------------|
| `lookup_ticker(symbol)` | Busca información completa de un ticker. Retorna `AssetLookup` o `None` |
| `get_price(symbol)` | Obtiene precio actual y variación diaria. Retorna `PriceSnapshot` o `None` |
| `get_prices_batch(symbols)` | Precios de múltiples tickers. Retorna `dict[str, PriceSnapshot]` |
| `get_history(symbol, period)` | Histórico OHLCV. Periodos: `1d`, `5d`, `1mo`, `3mo`, `6mo`, `1y`, `2y`, `5y`, `10y`, `ytd`, `max` |

## Endpoints API

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/api/market/lookup/{ticker}` | Auto-fill: busca info de un activo |
| `GET` | `/api/market/price/{ticker}` | Precio actual + variación |
| `POST` | `/api/market/prices` | Precios en lote (body: `{"tickers": [...]}`) |
| `GET` | `/api/market/history/{ticker}?period=1y` | Histórico OHLCV |

## Dependencias

- `yfinance` — acceso a Yahoo Finance API
- `pydantic` — validación de modelos

## Relación con otros módulos

```
Market ──▸ Analytics   (históricos de precios para calcular retornos)
       ──▸ Advisor     (precios reales para enriquecer recomendaciones)
       ──▸ Portfolio   (auto-fill de activos al crear cartera en frontend)
```

## Consideraciones

- Yahoo Finance es para uso personal/educativo; datos con retraso de 15-20 min en algunos mercados.
- Las llamadas son síncronas (yfinance no soporta async nativamente).
- `get_prices_batch` itera secuencialmente; para muchos tickers puede ser lento.
- Los errores se gestionan con try/except y logging, retornando `None` si falla.
