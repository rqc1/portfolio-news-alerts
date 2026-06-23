# Módulo de Evaluación

Evaluación cuantitativa del pipeline InvestAIlert sobre un corpus etiquetado
manualmente. Calcula métricas estándar de NLP (precision/recall/F1, MAE
ordinal) y permite ejecutar un **ablation study** comparando cuatro variantes
del pipeline.

---

## Estructura

```
evaluation/
├── __init__.py
├── schema.py             # Pydantic: GoldLabels, LabeledNews, PipelinePrediction
├── dataset.jsonl         # Corpus etiquetado (40 noticias, 3 carteras, ES + EN)
├── portfolios.json       # Carteras de referencia (tech_us, iberico, energia)
├── metrics.py            # P/R/F1 binario, multiclase, set-based, MAE ordinal
├── runner.py             # PipelineRunner con 4 variantes (ablation)
├── run_ablation.py       # CLI principal: orquesta el ablation study
└── results/              # Salidas por variante (creado al ejecutar)
    ├── <variant>_predictions.jsonl
    ├── <variant>_metrics.json
    └── ablation_summary.json
```

---

## Ejecución

```bash
# Todas las variantes (rules → hybrid → hybrid_nli → full)
python -m evaluation.run_ablation

# Solo variantes concretas
python -m evaluation.run_ablation --variants rules hybrid

# Tests unitarios del módulo
pytest tests/test_evaluation.py -v
```

> Nota: las variantes `hybrid_nli` y `full` cargan FinBERT + BART-MNLI
> + sentence-transformers (~3 GB RAM, ~3-5 min/variante en CPU). La variante
> `rules` se ejecuta en segundos.

---

## Variantes del ablation

| Variante | Relevancia | Eventos | Impacto | LLM |
|----------|:----------:|:-------:|:-------:|:---:|
| `rules` | rule-based | – | – | – |
| `hybrid` | rule-based + embeddings | – | – | – |
| `hybrid_nli` | rule-based + embeddings | FinBERT + zero-shot NLI | determinista | – |
| `full` | + LLM borderline rescue | FinBERT + NLI (refinado por LLM) | determinista + LLM contextual | ✅ |

`full` cae automáticamente a `hybrid_nli` si no hay API key del LLM
configurada (`GITHUB_TOKEN`, `OPENAI_API_KEY`…), así que el ablation
completo es ejecutable sin coste API.

---

## Métricas reportadas

| Etapa | Métrica | Justificación |
|-------|---------|---------------|
| **Relevancia** (binaria) | P / R / F1 / Accuracy + matriz de confusión | Es la decisión más crítica: filtra qué llega al usuario |
| **Matched assets** (set) | P / R / F1 micro-averaged + Jaccard medio + exact-match rate | Mide si los tickers detectados coinciden con el gold |
| **Tipo de evento** (multiclase) | Accuracy + macro-F1 + weighted-F1 + per-class P/R/F1 + matriz de confusión | macro-F1 penaliza el desbalance de clases (12 tipos en taxonomía) |
| **Dirección** (3 clases) | Accuracy + macro-F1 | alcista/bajista/neutral son equiprobables a priori |
| **Severidad** (ordinal) | **MAE** sobre escala 0-4 + exact-match + off-by-one | MAE respeta el orden (alta vs muy_alta es mejor que alta vs muy_baja) |

---

## Corpus

40 noticias etiquetadas a mano, distribuidas en:

- **3 carteras de referencia**: tecnológicas USA, ibérico diversificado, energía global
- **Bilingüe**: 21 EN + 19 ES (cubre el pipeline de traducción ES→EN)
- **Cobertura de taxonomía**: los 12 tipos de evento de `EVENT_TAXONOMY` aparecen al menos una vez
- **Negativos**: 5 noticias deliberadamente irrelevantes (deportes, clima, ciencia) para medir falsos positivos
- **Hard cases**: noticias que mencionan empresas no-cartera pero relevantes por sector (`ev007`, `ev032`), o cuya relevancia indirecta requiere razonamiento (`ev014` TSMC→Apple, `ev036` Google quantum→NVDA, `ev039` algodón→Inditex)

### Esquema de etiquetado

Cada ejemplo incluye:

```json
{
  "id": "ev001",
  "portfolio_id": "tech_us",
  "title": "...", "summary": "...", "content": "...",
  "labels": {
    "is_relevant": true,
    "matched_assets": ["AAPL"],
    "event_type": "resultados_empresariales",
    "direction": "alcista",
    "severity_label": "alta"
  }
}
```

### Limitaciones del corpus actual

- **Tamaño** (40): suficiente para detectar tendencias y falsos positivos
  evidentes, insuficiente para conclusiones estadísticamente robustas. Ampliar
  a ≥200 ejemplos para resultados publicables.
- **Sintético en parte**: las noticias están redactadas (no extraídas de la
  ingesta real) para garantizar cobertura uniforme de la taxonomía.

---

## Fiabilidad del etiquetado: acuerdo inter-anotador (IAA)

Para sostener la validez del ground truth, un subconjunto de **25 noticias**
(`dataset_annotator2.jsonl`) fue re-anotado de forma **independiente** por un
segundo anotador siguiendo la misma guía. El acuerdo se mide con
`evaluation/agreement.py` (implementación pura, sin sklearn):

```bash
python -m evaluation.run_agreement
# → evaluation/results/agreement.json
```

Métricas por dimensión (sobre los 25 ítems comunes):

| Dimensión | % acuerdo | Estadístico | Valor | Interpretación |
|-----------|:---------:|-------------|:-----:|----------------|
| `is_relevant` | 0.96 | κ de Cohen | **0.86** | casi perfecto |
| `event_type` | 1.00 | κ de Cohen | **1.00** | casi perfecto |
| `direction` | 0.92 | κ de Cohen | **0.88** | casi perfecto |
| `severity_label` | 0.56 | κ ponderado (cuadrático) | **0.82** | casi perfecto |
| `severity_label` | 0.56 | α de Krippendorff (ordinal) | **0.91** | casi perfecto |

Notas metodológicas:

- **Severidad**: el acuerdo exacto es bajo (0.56) porque es la dimensión más
  subjetiva, pero los desacuerdos son casi siempre **entre categorías
  adyacentes** (alta vs muy_alta). Por eso se reporta κ **ponderado** y α
  **ordinal**, que penalizan menos los desacuerdos cercanos y revelan un
  acuerdo sustancial (0.82–0.91). Reportar solo κ nominal infravaloraría la
  fiabilidad real de una variable ordinal.
- **Escala de interpretación**: Landis & Koch (1977) — <0.20 leve, 0.21–0.40
  aceptable, 0.41–0.60 moderado, 0.61–0.80 sustancial, 0.81–1.00 casi perfecto.

### Guía de anotación

Reglas aplicadas por ambos anotadores (resumen operativo):

1. **`is_relevant`**: marcar `true` si la noticia afecta —directa o
   indirectamente por sector/cadena de suministro— a algún activo de la
   `portfolio_id` indicada. Noticias de deporte, clima o ciencia sin vínculo
   económico → `false`.
2. **`matched_assets`**: incluir solo tickers de la cartera con vínculo
   **explícito o causal claro**. Una mención de un proveedor (TSMC→AAPL) o un
   competidor relevante (Google quantum→NVDA) justifica el ticker afectado,
   no el de la empresa citada si no está en cartera.
3. **`event_type`**: asignar el tipo dominante de la taxonomía
   `EVENT_TAXONOMY`. Ante ambigüedad, priorizar el evento con mayor impacto
   potencial sobre el precio.
4. **`direction`**: `alcista`/`bajista`/`neutral` según el efecto esperado
   sobre el activo (no sobre el sentimiento del texto). Reestructuraciones,
   OPAs y cambios directivos sin sesgo claro → `neutral`.
5. **`severity_label`** (ordinal): calibrar por la magnitud esperada del
   movimiento de precio: `muy_baja` (<0.5%), `baja` (0.5–1.5%),
   `media` (1.5–3%), `alta` (3–6%), `muy_alta` (>6%). Estas bandas se
   alinean con `modules/impact/calibration.py`.

### Limitaciones residuales

- **Tamaño** (40 total / 25 doble-anotados): suficiente para estimar IAA y
  detectar tendencias, insuficiente para conclusiones estadísticamente
  robustas. Ampliar a ≥200 ejemplos y ≥3 anotadores (habilita κ de Fleiss,
  ya implementado en `agreement.py`) para resultados publicables.

---

## Resultados base (referencia)

Ejemplo de ejecución de `rules` sobre el corpus semilla (40 ejemplos):

```
--- Relevancia (binaria) ---
  P=1.000  R=0.879  F1=0.935  Acc=0.900  (TP=29 FP=0 FN=4 TN=7)

--- Matched assets (micro-avg sobre conjuntos) ---
  P=1.000  R=1.000  F1=1.000
```

**Lectura**: el matching directo (word-boundary regex sobre tickers, nombres
y aliases) ya logra precisión perfecta. Los 4 falsos negativos son noticias
de relevancia indirecta (sector, supply chain, regulación que afecta a la
industria) que requieren la capa semántica o el rescate por LLM. Esto motiva
empíricamente la arquitectura híbrida.

---

## Cómo ampliar el corpus

1. Edita `evaluation/dataset.jsonl` añadiendo una línea JSON por ejemplo.
2. Si la noticia es para una cartera nueva, defínela en `portfolios.json`.
3. Asegura coherencia: si `is_relevant=false`, deja `matched_assets=[]`,
   `event_type="otro"`, `direction="neutral"`, `severity_label="muy_baja"`.

---

## Comparación Multi-Modelo LLM

Además del ablation study (que evalúa las 4 variantes del pipeline NLP),
se ejecutó una **comparación de 7 modelos LLM** para el módulo de análisis
contextual (`modules/llm/analyzer.py`).

### Script

```bash
python scripts/compare_models.py
```

### Modelos evaluados (v2.0, 2026-06-03)

| Modelo | Proveedor | Errores | Confianza | Latencia | Ranking |
|--------|-----------|---------|-----------|----------|---------|
| GPT-4o | OpenAI (GitHub) | 0/10 | 0.815 | 2.8s | **#1** |
| Llama-3.1-8B | Meta (GitHub) | 0/10 | 0.825 | 1.7s | #2 |
| Llama-3.1-405B | Meta (GitHub) | 0/10 | 0.800 | 6.5s | #3 |
| Llama-3.3-70B | Meta (GitHub) | 1/10 | 0.800 | 3.0s | #4 |
| GPT-4o-mini | OpenAI (GitHub) | 0/10 | 0.730 | 3.5s | #5 |
| DeepSeek-V3 | DeepSeek (GitHub) | 2/10 | 0.775 | 22.3s | #6 |
| DeepSeek-R1 | DeepSeek (GitHub) | 2/10 | 0.719 | 8.5s | #7 |

**Descartados**: Phi-4 (timeout 75%), Phi-4-reasoning (JSON inválido 100%).

### Hallazgos clave

- **Acuerdo en dirección >85%** en noticias con señal clara (ciberincidentes, regulación).
- **DeepSeek-V3** tiene acuerdo perfecto (100%) en tipo de evento con GPT-4o.
- Las noticias anticipatorias (resultados pendientes) generan mayor divergencia.
- Los errores de DeepSeek son por **rate limiting 429** del free tier, no por calidad.

### Artefactos

- `scripts/model_comparison_results.json` — datos crudos con explicaciones LLM completas
- `evaluation/results/model_comparison_report.json` — informe estructurado v2.0
4. Los tests `tests/test_evaluation.py::test_dataset_labels_consistency` y
   `test_load_portfolios` verifican estas invariantes automáticamente.

---

## Trabajo futuro

- **Calibración de probabilidades**: aplicar Platt/isotonic sobre `severity`
  y `confidence` usando el corpus etiquetado, validado por reliability
  diagrams.
- **Event study financiero**: para cada alerta con ticker, calcular CAR
  (Cumulative Abnormal Return) en ventana [-1, +3] días con `yfinance` y
  comparar contra noticias no-relevantes (control group).
- **Inter-annotator agreement**: re-etiquetar con un segundo anotador y
  reportar Cohen's κ por columna.
- **Bootstrap CI**: intervalos de confianza de las métricas mediante 1000
  resamples bootstrap del corpus.
