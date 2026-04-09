# Módulo 5 — Events (Clasificación de Eventos)

## Propósito

Clasifica cada noticia en **dos dimensiones ortogonales**:

1. **Sentimiento financiero** — positivo / negativo / neutral — vía FinBERT.
2. **Tipo de evento** — una de 12 categorías de la taxonomía — vía LLM (con fallback a keywords).

Esta doble clasificación permite al pipeline distinguir, por ejemplo, entre
"resultados empresariales positivos" y "resultados empresariales negativos" — misma
categoría de evento pero impacto financiero opuesto.

## Archivos

| Archivo | Qué contiene |
|---------|-------------|
| `classifier.py` | `FinBERTSentiment`, `LLMEventClassifier`, `EventClassificationService` |

## Componentes

### `FinBERTSentiment`

Modelo de Hugging Face [`ProsusAI/finbert`](https://huggingface.co/ProsusAI/finbert),
fine-tuneado sobre 10.000+ noticias financieras (Financial PhraseBank).

```python
def analyze(text: str) → dict:
    return {
        "label": "positive" | "negative" | "neutral",
        "score": float,       # confianza del softmax (0–1)
        "probabilities": {    # distribución completa
            "positive": float,
            "negative": float,
            "neutral": float
        }
    }
```

- Trunca a 512 tokens (límite de BERT).
- Se carga una sola vez y se reutiliza (singleton en memoria).

### `LLMEventClassifier`

Envía el texto a **OpenAI GPT-4o-mini** con un prompt estructurado que incluye
las 12 categorías de la taxonomía y solicita respuesta JSON:

```json
{
  "event_type": "fusion_adquisicion",
  "confidence": 0.85,
  "reasoning": "The article describes a $30B acquisition bid..."
}
```

#### Fallback por keywords

Si no hay `OPENAI_API_KEY` o la llamada falla, se activa `_fallback_classify()`:
diccionario de keywords por categoría. La primera categoría cuyas keywords aparezcan
en el texto gana.

| Categoría | Keywords (muestra) |
|-----------|--------------------|
| `resultados_empresariales` | earnings, revenue, EPS, quarterly results |
| `fusion_adquisicion` | merger, acquisition, takeover, buyout |
| `ciberincidente` | data breach, ransomware, cyberattack, hacked |
| `macroeconomia` | interest rate, inflation, GDP, unemployment |
| ... | ... |

### `EventClassificationService`

Combina ambos:

```python
def classify(text: str) → dict:
    return {
        "sentiment": FinBERTSentiment.analyze(text),
        "event": LLMEventClassifier.classify(text),   # o fallback
    }
```

## Taxonomía Completa (12 categorías)

| # | Código | Descripción |
|---|--------|-------------|
| 1 | `resultados_empresariales` | Earnings, EPS, revenue, quarterly/annual results |
| 2 | `guidance_profit_warning` | Forward guidance, profit warnings, outlook revisions |
| 3 | `regulacion` | Regulatory actions, fines, sanctions, policy changes |
| 4 | `litigio` | Lawsuits, legal proceedings, SEC investigations |
| 5 | `fusion_adquisicion` | M&A, takeovers, joint ventures, divestitures |
| 6 | `ciberincidente` | Data breaches, ransomware, cyberattacks |
| 7 | `incidencia_operativa` | Outages, product recalls, operational failures |
| 8 | `macroeconomia` | Interest rates, inflation, GDP, central bank decisions |
| 9 | `cadena_suministro` | Logistics disruptions, shortages, raw materials |
| 10 | `cambio_directivo` | CEO changes, board appointments, resignations |
| 11 | `dividendo_recompra` | Dividends, share buybacks, capital returns |
| 12 | `otro` | Events not matching any specific category |

## Dependencias

- `transformers` + `torch` — FinBERT inference
- `openai` — API para clasificación LLM (opcional)
- `config.py` — modelo, taxonomía, API key

## Relación con otros módulos

```
NLP ──▸ Events ──▸ Impact  (tipo de evento + sentimiento determinan dirección y severidad)
```
