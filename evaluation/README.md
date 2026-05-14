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
- **Etiquetador único**: sin medida de inter-annotator agreement (Cohen's κ).
- **Sintético en parte**: las noticias están redactadas (no extraídas de la
  ingesta real) para garantizar cobertura uniforme de la taxonomía.

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
