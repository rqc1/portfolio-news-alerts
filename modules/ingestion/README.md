# Módulo 2 — Ingestion (Adquisición de Noticias)

## Propósito

Adquiere noticias de múltiples fuentes heterogéneas, las normaliza a un schema
común (`NewsItem`) y las persiste en MongoDB con deduplicación por hash de contenido.
Actúa como el "sensor" del sistema: sin ingesta, el pipeline no tiene datos que procesar.

## Archivos

| Archivo | Qué contiene |
|---------|-------------|
| `models.py` | Schema `NewsItem` — modelo unificado de noticia |
| `rss_feeds.py` | Parser de feeds RSS (22 feeds en 5 categorías) |
| `sec_edgar.py` | Cliente async para la API de SEC EDGAR |
| `cnmv.py` | Parser de feeds RSS de la CNMV |
| `newsapi.py` | Integración con NewsAPI.org (texto completo) |
| `alphavantage.py` | Integración con Alpha Vantage News Sentiment |
| `service.py` | `IngestionService` — orquestador de todas las fuentes |

## Modelo de Datos: `NewsItem`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `title` | `str` | Titular de la noticia |
| `summary` | `str` | Resumen o texto introductorio |
| `content` | `str?` | Texto completo (si está disponible) |
| `url` | `str` | URL canónica (clave de deduplicación) |
| `source` | `str` | Identificador de la fuente |
| `source_type` | `str` | `rss`, `sec_edgar`, `cnmv`, `newsapi`, `alphavantage` |
| `published_at` | `datetime` | Fecha de publicación |
| `language` | `str?` | Código ISO 639-1 (`en`, `es`) |
| `content_hash` | `str` | SHA-256 del contenido (dedup secundario) |
| `entities_raw` | `list[str]` | Entidades extraídas pre-NLP (si la fuente las aporta) |
| `metadata` | `dict` | Metadatos específicos de la fuente |

## Fuentes Implementadas

### RSS Feeds (22 feeds, 5 categorías)

| Categoría | Feeds | Sin API key |
|-----------|-------|:-----------:|
| Finanzas generales | Reuters Business, Reuters Markets, Yahoo Finance, FT, Seeking Alpha, Investing.com, MarketWatch, CNBC, Bloomberg | ✅ |
| Macroeconomía | ECB Press, Fed News, BoE News, IMF Blog | ✅ |
| Prensa española | Expansión, Cinco Días, El Economista | ✅ |
| Ciberseguridad | BleepingComputer, The Hacker News, SecurityWeek | ✅ |
| Cadena de suministro | Supply Chain Dive, FreightWaves | ✅ |

### SEC EDGAR

- **Búsqueda full-text**: `search_recent_filings(query)` — busca en texto libre de filings.
- **Por empresa**: `get_company_filings(cik)` — últimos filings de una empresa por CIK.
- Requiere `SEC_USER_AGENT` (nombre + email, exigido por la SEC).
- Enfoque en 8-K (eventos materiales), 10-K/10-Q (informes anuales/trimestrales).

### CNMV

- 3 feeds RSS: hechos relevantes, información privilegiada, notas de prensa.
- Contenido en español; etiquetado `language="es"`.

### NewsAPI.org

- `search_newsapi(query, language, from_date)` — búsqueda por palabras clave.
- `search_newsapi_for_tickers(tickers, language)` — búsqueda por lista de tickers.
- Devuelve texto completo cuando la fuente lo proporciona.
- Requiere `NEWSAPI_KEY`.

### Alpha Vantage

- `fetch_alphavantage_news(tickers, topics)` — noticias con sentiment ya calculado.
- Cada noticia viene con `ticker_sentiment`: lista de tickers mencionados + score.
- Topics opcionales: `earnings`, `ipo`, `mergers_and_acquisitions`, `financial_markets`, etc.
- Requiere `ALPHAVANTAGE_KEY`.

## `IngestionService`

| Método | Descripción |
|--------|-------------|
| `ingest_all(query, tickers)` | Ejecuta **todas** las fuentes en paralelo |
| `ingest_rss_only()` | Solo los 22 feeds RSS |
| `ingest_cnmv_only()` | Solo los 3 feeds CNMV |
| `ingest_newsapi(query, language)` | Solo NewsAPI |
| `ingest_alphavantage(tickers, topics)` | Solo Alpha Vantage |
| `get_recent_news(limit)` | Recupera noticias recientes de MongoDB |

### Deduplicación

Dos niveles de deduplicación:

1. **Por URL** — índice unique en MongoDB; si la URL ya existe, DuplicateKeyError se captura silenciosamente.
2. **Por `content_hash`** — SHA-256 del título + resumen; detecta la misma noticia publicada en URLs diferentes.

## Dependencias

- `feedparser` — parsing de RSS/Atom
- `httpx` — HTTP async para SEC EDGAR, NewsAPI, Alpha Vantage
- `hashlib` — SHA-256 para content_hash
- `database.mongodb.MongoDB` — persistencia
- `config.py` — URLs de feeds, API keys

## Relación con otros módulos

```
Ingestion ──▸ NLP          (las noticias ingestadas pasan al preprocesado)
          ──▸ AlertEngine  (engine.process_batch lee noticias de la colección news)
```
