# Módulo 6 — Impact (Estimación de Impacto)

## Propósito

Estima la **dirección** (alcista / bajista / neutral), **severidad** (0.0–1.0) y
**confianza** del impacto potencial de un evento detectado sobre los activos
afectados de la cartera.

Opera en **dos modos complementarios**:

1. **Determinista** — Combina priors empíricos por tipo de evento con el sentimiento FinBERT y el score de relevancia. Siempre disponible, sin coste.
2. **Contextual (LLM)** — El módulo `llm.ContextualAnalyzer` analiza el contexto completo (noticia + cartera) y produce estimaciones más matizadas. Si está disponible, sus resultados se fusionan con los deterministas vía `merge_with_llm()`.

## Archivos

| Archivo | Qué contiene |
|---------|-------------|
| `estimator.py` | `ImpactEstimator` + diccionario `EVENT_IMPACT_PRIORS` |

## Modelo de Estimación

La estimación sigue una fórmula compuesta:

```
severidad_final = base_severity × sentiment_amplifier × relevance_score × asset_factor
```

### 1. Priors por Tipo de Evento (`EVENT_IMPACT_PRIORS`)

Cada tipo de evento tiene una **severidad base** y un **sesgo de dirección**
calibrados a partir de la literatura financiera sobre event studies:

| Evento | Severidad base | Sesgo de dirección |
|--------|:--------------:|:------------------:|
| `resultados_empresariales` | 0.6 | 0.0 (neutral) |
| `guidance_profit_warning` | 0.7 | -0.3 (bajista) |
| `regulacion` | 0.6 | -0.2 (bajista) |
| `litigio` | 0.5 | -0.3 (bajista) |
| `fusion_adquisicion` | 0.7 | 0.0 (neutral) |
| `ciberincidente` | 0.8 | -0.5 (muy bajista) |
| `incidencia_operativa` | 0.5 | -0.2 (bajista) |
| `macroeconomia` | 0.6 | 0.0 (neutral) |
| `cadena_suministro` | 0.5 | -0.2 (bajista) |
| `cambio_directivo` | 0.5 | 0.0 (neutral) |
| `dividendo_recompra` | 0.4 | +0.3 (alcista) |
| `otro` | 0.3 | 0.0 (neutral) |

### 2. Amplificación por Sentimiento

La dirección del sentimiento (FinBERT) refuerza o invierte el sesgo del prior:

- **Sentimiento + sesgo alineados** → se refuerza (e.g., ciberincidente + negative = severidad ↑).
- **Sentimiento contra sesgo** → se atenúa (e.g., litigio + positive = severidad ↓).

### 3. Amplificación por Relevancia

El score de relevancia del módulo 4 actúa como multiplicador:

- Relevancia 0.9 (match directo) → severidad casi intacta.
- Relevancia 0.5 (umbral mínimo) → severidad se reduce a la mitad.

### 4. Factor de Activos

Si la noticia afecta a múltiples activos de la cartera simultáneamente, la
severidad se amplifica ligeramente (mayor exposición del portfolio).

## Output determinista

```python
def estimate(event_type, sentiment, relevance_score, matched_assets) → dict:
    return {
        "direction": "alcista" | "bajista" | "neutral",
        "severity": float,          # 0.0 – 1.0
        "severity_label": str,      # "baja" | "media" | "alta" | "crítica"
        "confidence": float,        # 0.0 – 1.0 (media ponderada de confianzas)
        "event_type": str,
        "matched_assets": list[str]
    }
```

## Fusión con LLM (`merge_with_llm`)

Método estático que combina la estimación determinista con el análisis contextual del LLM:

```python
@staticmethod
def merge_with_llm(deterministic: dict, llm_analysis: dict | None) → dict:
    # Si llm_analysis es None → devuelve deterministic sin cambios
    # Si llm_analysis existe:
    #   - direction, severity, confidence → del LLM (más contextualizados)
    #   - direction_score → del determinista (referencia numérica)
    #   - llm_enhanced: True (flag de trazabilidad)
```

| Campo | Sin LLM | Con LLM |
|-------|---------|----------|
| `direction` | Fórmula determinista | LLM contextual |
| `severity` | Prior × amplificadores | LLM contextual |
| `confidence` | Media ponderada | LLM contextual |
| `direction_score` | Calculado | Calculado (referencia) |
| `llm_enhanced` | Ausente | `True` |

### Escala de Severidad

| Rango | Label | Significado |
|-------|-------|-------------|
| 0.0 – 0.3 | Baja | Impacto marginal, probablemente noise |
| 0.3 – 0.6 | Media | Impacto moderado, merece atención |
| 0.6 – 0.8 | Alta | Impacto significativo, requiere revisión |
| 0.8 – 1.0 | Crítica | Impacto potencialmente material, acción recomendada |

## Umbral de Severidad

Configurable en `config.py` → `SEVERITY_THRESHOLD = 0.3`.
Estimaciones con severidad < 0.3 no generan alerta.

## Dependencias

- `numpy` — cálculos numéricos
- Entrada: output del módulo Events (tipo + sentimiento)
- Entrada: output del módulo Relevance (score + activos afectados)
- Opcional: output del módulo LLM (`ContextualAnalyzer`) para fusión contextual

## Relación con otros módulos

```
Events ────┐
           ├──▸ Impact (determinista) ──┐
Relevance ─┘                            ├──▸ merge_with_llm() ──▸ AlertEngine
           LLM ContextualAnalyzer ──────┘
```
