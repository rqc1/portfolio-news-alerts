# Módulo 4 — Relevance (Relevancia por Cartera)

## Propósito

Determina **cuánto importa una noticia para una cartera concreta**, asignando un score
de relevancia entre 0.0 y 1.0 y una razón textual. Combina dos estrategias
complementarias:

1. **Reglas explícitas** — matching directo por ticker/nombre/alias, entidades NER, sector y país.
2. **Similitud semántica** — cosine similarity entre embeddings de la noticia y la descripción de la cartera.

## Archivos

| Archivo | Qué contiene |
|---------|-------------|
| `service.py` | `RuleBasedRelevance`, `SemanticRelevance`, `RelevanceService` |

## Componentes

### `RuleBasedRelevance`

Busca coincidencias entre el texto de la noticia y los identificadores de la cartera.
Usa **word-boundary matching** (`\\b` regex) para nombres cortos (≤3 chars) y palabras
comunes en inglés ("a", "it", "ai", "us", "or", "all"), evitando falsos positivos
como `"US"` matcheando con "bec**us**e".

| Tipo de match | Score | Prioridad | Ejemplo |
|---------------|:-----:|:---------:|---------|
| **Ticker directo** | 0.9 | Alta | `AAPL` aparece en el título |
| **Nombre / alias directo** | 0.9 | Alta | `Apple` en el texto |
| **Entidad NER → activo** | 0.8 | Media-Alta | NER extrae `Apple Inc.` y coincide con asset |
| **Sector** | 0.5 | Media | Noticia sobre `Technology` y cartera tiene activos tech |
| **País** | 0.3 | Baja | Noticia sobre `España` y cartera tiene activos ES |

Devuelve el **match de mayor score** junto con los activos afectados.

### `SemanticRelevance`

Construye un "resumen semántico" de la cartera a partir de los nombres y sectores de sus activos,
calcula un embedding con `sentence-transformers/all-MiniLM-L6-v2`, y compara con el embedding
del texto de la noticia usando **cosine similarity**.

- Score ∈ [0.0, 1.0]
- No requiere mención literal de nombres; captura similitud conceptual.
- Ejemplo: noticia sobre "chip shortage affects tech manufacturing" tiene alta similitud
  semántica con una cartera que contiene `AAPL`, `MSFT`, `NVDA`.

### `RelevanceService`

Combina ambos scorers con pesos adaptativos según el tipo de match:

| Tipo de match | Peso reglas | Peso semántico | Lógica |
|---------------|:-----------:|:--------------:|--------|
| Match directo (ticker/nombre) | 70% | 30% | Prioriza evidencia explícita |
| Match sectorial | 50% | 50% | Equilibrado |
| Match bajo / sin match | 30% | 70% | Depende más de la semántica |

```python
def evaluate(news_text, entities, portfolio) → dict:
    return {
        "score": float,           # 0.0 – 1.0
        "reason": str,            # "Mención directa de AAPL"
        "matched_assets": list,   # [Asset, ...]
        "match_type": str         # "direct" | "entity" | "sector" | "country" | "semantic"
    }
```

## Umbral de Relevancia

Configurable en `config.py`:

| Parámetro | Default | Efecto |
|-----------|:-------:|--------|
| `RELEVANCE_THRESHOLD` | 0.5 | Noticias con score ≥ 0.5 pasan directamente |
| `ALERT_RELEVANCE_BORDERLINE` | 0.3 | Límite inferior de la zona borderline |

### Zona borderline (0.3 – 0.5)

Las noticias con score entre 0.3 y 0.5 entran en una **zona borderline** donde
el `AlertEngine` consulta al **LLM RelevanceChecker** (`modules.llm.analyzer`).

El LLM analiza si la noticia tiene **efectos indirectos** sobre la cartera:
- Competidores directos afectados
- Proveedores o clientes de activos en cartera
- Cambios regulatorios sectoriales
- Impacto macroeconómico sobre el sector

```python
# En AlertEngine (paso 3b):
if ALERT_RELEVANCE_BORDERLINE <= score < RELEVANCE_THRESHOLD:
    llm_result = relevance_checker.check(news, portfolio)
    if llm_result and not llm_result["is_relevant"]:
        return None  # descartada por LLM
    # Si LLM no disponible o dice relevante → continúa
```

Si el LLM no está disponible, las noticias borderline pasan al siguiente paso
(degradación elegante — preferimos un falso positivo a silenciar una alerta).

## Dependencias

- `sentence-transformers` — embeddings semánticos (`all-MiniLM-L6-v2`)
- `numpy` — cálculo de cosine similarity
- Entrada: texto limpio + entidades del módulo NLP
- Entrada: objeto Portfolio del módulo Portfolio
- Opcional: `modules.llm.analyzer.RelevanceChecker` para zona borderline (invocado desde AlertEngine)

## Relación con otros módulos

```
Portfolio ──┐
            ├──▸ Relevance ──▸ Events (si score ≥ 0.5)
NLP ────────┘               ──▸ LLM RelevanceChecker (si 0.3 ≤ score < 0.5)
                             ──▸ Impact (el score de relevancia amplifica la severidad)
```
