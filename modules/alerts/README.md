# Módulo 7 — Alerts (Motor de Alertas)

## Propósito

Módulo final del pipeline. Recibe las salidas de todos los módulos anteriores y decide
si emitir una alerta, aplicando filtros de calidad, deduplicación semántica y
control anti-spam. Si la alerta pasa todos los filtros, genera una **explicación
en lenguaje natural** (español) y la persiste en MongoDB.

Es el único módulo que orquesta todo el pipeline de principio a fin.

## Archivos

| Archivo | Qué contiene |
|---------|-------------|
| `engine.py` | `AlertEngine` — orquestador del pipeline + modelo `Alert` |
| `deduplication.py` | `SemanticDeduplicator` — dedup por embeddings |
| `explainer.py` | `AlertExplainer` — generación de explicaciones |

## Componentes

### `AlertEngine`

Orquesta el pipeline completo para cada noticia:

```
Noticia
  │
  ├─ 1. Anti-spam check (≤ 20 alertas/hora)
  │
  ├─ 2. NLP preprocessing (limpieza + NER + idioma)
  │
  ├─ 3. Relevance scoring (reglas + semántico)
  │     └─ score < 0.5 → descartada
  │
  ├─ 4. Event classification (FinBERT + LLM/keywords)
  │
  ├─ 5. Impact estimation (dirección + severidad + confianza)
  │     └─ severity < 0.3 → descartada
  │
  ├─ 6. Semantic deduplication
  │     └─ similitud > 0.85 con alerta reciente → descartada
  │
  ├─ 7. Explanation generation (texto en español)
  │
  └─ 8. Persistencia en MongoDB (colección alerts)
```

**Métodos principales:**

| Método | Descripción |
|--------|-------------|
| `process_news(news_item, portfolio)` | Procesa una noticia; devuelve `Alert` o `None` |
| `process_and_store(news_item, portfolio)` | Procesa + persiste en MongoDB |
| `process_batch(portfolio_id, limit)` | Procesa batch de noticias recientes contra una cartera |

### `Alert` (Pydantic model)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `portfolio_id` | `str` | Cartera afectada |
| `news_title` | `str` | Titular de la noticia |
| `news_url` | `str` | URL de la fuente |
| `news_source` | `str` | Identificador de fuente |
| `event_type` | `str` | Categoría de evento (taxonomía) |
| `sentiment` | `str` | positive / negative / neutral |
| `direction` | `str` | alcista / bajista / neutral |
| `severity` | `float` | 0.0 – 1.0 |
| `severity_label` | `str` | baja / media / alta / crítica |
| `confidence` | `float` | 0.0 – 1.0 |
| `matched_assets` | `list[str]` | Tickers afectados |
| `relevance_score` | `float` | Score de relevancia |
| `relevance_reason` | `str` | Explicación del match |
| `explanation` | `str` | Explicación en lenguaje natural |
| `created_at` | `datetime` | Timestamp de creación |

### `SemanticDeduplicator`

Evita alertas redundantes comparando embeddings semánticos:

- Mantiene un **buffer circular de 200** embeddings de alertas recientes.
- Para cada nueva alerta, calcula cosine similarity con el buffer.
- Si similarity > **0.85** → la marca como duplicada y no se emite.
- Embeddings calculados con `all-MiniLM-L6-v2`.

**¿Por qué semántica y no por URL?**
Dos noticias con URLs diferentes pueden cubrir el mismo evento
(Reuters y FT publican sobre los mismos resultados de Apple). La
deduplicación semántica captura estos duplicados conceptuales.

### `AlertExplainer`

Genera explicaciones en español a partir de los datos estructurados:

```python
def generate(alert_data: dict) → str:
    # Ejemplo de output:
    # "Posible alerta bajista de severidad alta para AAPL.
    #  Evento detectado: Litigio / procedimiento legal.
    #  Relevancia: mención directa de activo en cartera;
    #  sentimiento negative detectado por FinBERT.
    #  Confianza: 0.81.
    #  Fuente: reuters_business."
```

La explicación es **trazable**: cada afirmación está vinculada a un paso
concreto del pipeline (relevancia, FinBERT, tipo de evento, fuente).

## Umbrales Configurables

Todos en `config.py`:

| Parámetro | Default | Efecto |
|-----------|:-------:|--------|
| `RELEVANCE_THRESHOLD` | 0.5 | Noticias con score menor se descartan |
| `SEVERITY_THRESHOLD` | 0.3 | Estimaciones con severidad menor no generan alerta |
| `DEDUP_SIMILARITY_THRESHOLD` | 0.85 | Por encima de esto se considera duplicado |
| `MAX_ALERTS_PER_HOUR` | 20 | Anti-spam: máximo de alertas por hora |

## Dependencias

- `sentence-transformers` — embeddings para deduplicación
- `numpy` — cosine similarity
- `datetime` — timestamps y control anti-spam
- `database.mongodb.MongoDB` — persistencia de alertas
- Todos los módulos anteriores: NLP, Relevance, Events, Impact

## Relación con otros módulos

```
NLP ──────────┐
Relevance ────┤
Events ───────┼──▸ AlertEngine ──▸ MongoDB (colección alerts)
Impact ───────┤                ──▸ Frontend (Streamlit / API)
Portfolio ────┘
```
