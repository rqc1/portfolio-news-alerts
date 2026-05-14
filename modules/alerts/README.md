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
  │     ├─ score < 0.3 → descartada
  │     └─ score 0.3–0.5 (zona borderline) → LLM RelevanceChecker
  │           ├─ LLM dice "no relevante" → descartada
  │           └─ LLM dice "relevante" o LLM no disponible → continúa
  │
  ├─ 4. Event classification (FinBERT + zero-shot NLI / keywords)
  │
  ├─ 5. Impact estimation determinista (priors + sentimiento + relevancia)
  │     └─ severity < 0.3 → descartada
  │
  ├─ 6. LLM Contextual Analysis (ContextualAnalyzer)
  │     └─ Analiza noticia + cartera → dirección, severidad, confianza, explicación
  │     └─ merge_with_llm() fusiona resultado con estimación determinista
  │
  ├─ 7. Semantic deduplication
  │     └─ similitud > 0.85 con alerta reciente → descartada
  │
  ├─ 8. Explanation generation (LLM contextual o template)
  │
  └─ 9. Persistencia en MongoDB (colección alerts)
```

**Degradación elegante:** Si el LLM no está disponible, los pasos 3b (borderline) y
6 (contextual) se omiten automáticamente y el pipeline funciona con las estimaciones
deterministas y explicaciones por template, igual que antes de la integración LLM.

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

Evita alertas redundantes comparando embeddings semánticos a **dos niveles**:

1. **Caché en memoria** (rápido): buffer circular de 200 embeddings recientes.
2. **MongoDB persistente** (sobrevive reinicios): colección `dedup_embeddings` con los 500 últimos, TTL de 30 días.

- Para cada nueva alerta, calcula cosine similarity primero en memoria, luego en MongoDB si no hay match.
- Si similarity > **0.85** → la marca como duplicada y no se emite.
- Si es nueva, guarda el embedding en ambos niveles simultáneamente.
- Embeddings calculados con `all-MiniLM-L6-v2`.
- `is_duplicate()` es `async def` por las operaciones con MongoDB.

**¿Por qué semántica y no por URL?**
Dos noticias con URLs diferentes pueden cubrir el mismo evento
(Reuters y FT publican sobre los mismos resultados de Apple). La
deduplicación semántica captura estos duplicados conceptuales.

### `AlertExplainer`

Genera explicaciones en español. Opera en dos modos:

#### Modo LLM (preferido)

Si el `ContextualAnalyzer` produjo una explicación contextual, el explainer la
enriquece con metadatos de confianza y fuente:

```python
def generate(alert_data: dict, llm_explanation: str = "") → str:
    # Con LLM:
    # "Análisis contextual: La demanda colectiva contra Apple podría afectar
    #  su cotización dado que AAPL representa el 15% de su cartera.
    #  Confianza: 0.81. Fuente: reuters_business."
```

#### Modo template (fallback)

Si no hay explicación LLM, genera texto trazable a partir de datos estructurados:

```python
    # Sin LLM:
    # "Posible alerta bajista de severidad alta para AAPL.
    #  Evento detectado: Litigio / procedimiento legal.
    #  Relevancia: mención directa de activo en cartera;
    #  sentimiento negative detectado por FinBERT.
    #  Confianza: 0.81. Fuente: reuters_business."
```

Ambos modos son **trazables**: cada afirmación está vinculada a un paso
concreto del pipeline.

## Umbrales Configurables

Todos en `config.py`:

| Parámetro | Default | Efecto |
|-----------|:-------:|--------|
| `RELEVANCE_THRESHOLD` | 0.5 | Noticias con score menor se descartan (o van a zona borderline) |
| `ALERT_RELEVANCE_BORDERLINE` | 0.3 | Límite inferior de la zona borderline (LLM decide) |
| `SEVERITY_THRESHOLD` | 0.3 | Estimaciones con severidad menor no generan alerta |
| `DEDUP_SIMILARITY_THRESHOLD` | 0.85 | Por encima de esto se considera duplicado |
| `MAX_ALERTS_PER_HOUR` | 20 | Anti-spam: máximo de alertas por hora |

## Dependencias

- `sentence-transformers` — embeddings para deduplicación
- `numpy` — cosine similarity
- `datetime` — timestamps y control anti-spam
- `database.mongodb.MongoDB` — persistencia de alertas
- `modules.llm` — `ContextualAnalyzer` y `RelevanceChecker` (opcionales; degradación elegante)
- Todos los módulos anteriores: NLP, Relevance, Events, Impact

## Relación con otros módulos

```
NLP ──────────┐
Relevance ────┤
Events ───────┼──▸ AlertEngine ──▸ MongoDB (colección alerts)
Impact ───────┤                ──▸ Frontend (Next.js / API)
LLM ──────────┤
Portfolio ────┘
```
