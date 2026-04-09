# Módulo 1 — Portfolio (Modelado de Cartera)

## Propósito

Define la estructura de datos de las carteras de inversión y proporciona
operaciones CRUD asíncronas sobre MongoDB. Es el punto de partida del pipeline:
sin una cartera definida, el sistema no puede evaluar la relevancia de ninguna noticia.

## Archivos

| Archivo | Qué contiene |
|---------|-------------|
| `models.py` | Schemas Pydantic: `Asset` y `Portfolio` |
| `service.py` | `PortfolioService` — operaciones CRUD asíncronas |

## Modelos de Datos

### `Asset`

Representa un activo financiero dentro de una cartera.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `ticker` | `str` | Símbolo bursátil (e.g. `AAPL`, `SAN.MC`) |
| `name` | `str` | Nombre legal/completo |
| `isin` | `str?` | ISIN (opcional) |
| `sector` | `str?` | Sector GICS (e.g. `Technology`, `Financials`) |
| `industry` | `str?` | Sub-industria |
| `country` | `str?` | País de cotización (ISO 2) |
| `weight` | `float` | Peso en cartera (0.0–1.0) |
| `aliases` | `list[str]` | Nombres alternativos para matching (e.g. `["Apple"]`, `["Zara", "Inditex"]`) |

### `Portfolio`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `user_id` | `str` | Identificador del usuario |
| `name` | `str` | Nombre de la cartera |
| `assets` | `list[Asset]` | Composición de la cartera |

**Métodos helper** (devuelven datos agregados de la cartera):
- `get_tickers()` → todos los tickers
- `get_sectors()` → todos los sectores únicos
- `get_countries()` → todos los países únicos
- `get_all_names()` → tickers + names + aliases (para matching en el módulo de relevancia)

## `PortfolioService`

Métodos estáticos asíncronos:

| Método | Descripción |
|--------|-------------|
| `create_portfolio(data)` | Crea cartera, devuelve `portfolio_id` |
| `get_portfolio(id)` | Recupera una cartera por `_id` |
| `get_portfolios_by_user(user_id)` | Lista carteras de un usuario |
| `add_asset(portfolio_id, asset)` | Añade un activo (push to array) |
| `remove_asset(portfolio_id, ticker)` | Elimina activo por ticker (pull from array) |
| `delete_portfolio(id)` | Elimina la cartera completa |

## Dependencias

- `database.mongodb.MongoDB` — acceso a la colección `portfolios`
- `pydantic` — validación de modelos
- `bson.ObjectId` — IDs de MongoDB

## Relación con otros módulos

```
Portfolio ──▸ Relevance   (aporta tickers, sectores, países, aliases para scoring)
         ──▸ AlertEngine  (el pipeline necesita una cartera para procesar batch)
```
