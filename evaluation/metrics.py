"""
Métricas de evaluación.

Implementa cálculos puros (sin dependencias de sklearn) para mantener el
módulo ligero y reproducible:

  - Binary metrics: precision / recall / F1 / accuracy / confusion matrix
  - Multiclass metrics: per-class P/R/F1 + macro/weighted averages
  - Set metrics: Jaccard / per-instance precision-recall (matched_assets)
  - Ordinal metrics: MAE sobre severidad (muy_baja..muy_alta)

Devuelve estructuras serializables (dict) listas para JSON o tablas.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Iterable

from evaluation.schema import LabeledNews, PipelinePrediction


SEVERITY_ORDER = ["muy_baja", "baja", "media", "alta", "muy_alta"]
DIRECTION_LABELS = ["alcista", "bajista", "neutral"]


# ---------------------------------------------------------------------------
# Binary classification (relevance gate)
# ---------------------------------------------------------------------------
def binary_metrics(y_true: list[bool], y_pred: list[bool]) -> dict:
    """Precision, recall, F1, accuracy y matriz de confusión 2x2."""
    tp = sum(1 for t, p in zip(y_true, y_pred) if t and p)
    fp = sum(1 for t, p in zip(y_true, y_pred) if not t and p)
    fn = sum(1 for t, p in zip(y_true, y_pred) if t and not p)
    tn = sum(1 for t, p in zip(y_true, y_pred) if not t and not p)

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    accuracy = (tp + tn) / len(y_true) if y_true else 0.0

    return {
        "n": len(y_true),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "accuracy": round(accuracy, 4),
        "confusion_matrix": {"tp": tp, "fp": fp, "fn": fn, "tn": tn},
    }


# ---------------------------------------------------------------------------
# Multiclass classification (event_type, direction)
# ---------------------------------------------------------------------------
def multiclass_metrics(
    y_true: list[str],
    y_pred: list[str],
    labels: list[str] | None = None,
) -> dict:
    """P/R/F1 por clase + macro y weighted averages + matriz de confusión."""
    if labels is None:
        labels = sorted(set(y_true) | set(y_pred))

    per_class: dict[str, dict] = {}
    support_total = 0

    for label in labels:
        tp = sum(1 for t, p in zip(y_true, y_pred) if t == label and p == label)
        fp = sum(1 for t, p in zip(y_true, y_pred) if t != label and p == label)
        fn = sum(1 for t, p in zip(y_true, y_pred) if t == label and p != label)
        support = sum(1 for t in y_true if t == label)
        support_total += support

        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

        per_class[label] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "support": support,
        }

    # Averages
    if per_class:
        macro_p = sum(c["precision"] for c in per_class.values()) / len(per_class)
        macro_r = sum(c["recall"] for c in per_class.values()) / len(per_class)
        macro_f1 = sum(c["f1"] for c in per_class.values()) / len(per_class)

        if support_total > 0:
            weighted_p = sum(c["precision"] * c["support"] for c in per_class.values()) / support_total
            weighted_r = sum(c["recall"] * c["support"] for c in per_class.values()) / support_total
            weighted_f1 = sum(c["f1"] * c["support"] for c in per_class.values()) / support_total
        else:
            weighted_p = weighted_r = weighted_f1 = 0.0
    else:
        macro_p = macro_r = macro_f1 = 0.0
        weighted_p = weighted_r = weighted_f1 = 0.0

    accuracy = sum(1 for t, p in zip(y_true, y_pred) if t == p) / len(y_true) if y_true else 0.0

    # Confusion matrix
    cm: dict[str, dict[str, int]] = {l: {l2: 0 for l2 in labels} for l in labels}
    for t, p in zip(y_true, y_pred):
        if t in cm and p in cm[t]:
            cm[t][p] += 1

    return {
        "n": len(y_true),
        "accuracy": round(accuracy, 4),
        "macro": {
            "precision": round(macro_p, 4),
            "recall": round(macro_r, 4),
            "f1": round(macro_f1, 4),
        },
        "weighted": {
            "precision": round(weighted_p, 4),
            "recall": round(weighted_r, 4),
            "f1": round(weighted_f1, 4),
        },
        "per_class": per_class,
        "confusion_matrix": cm,
    }


# ---------------------------------------------------------------------------
# Set metrics (matched_assets) — micro-averaged P/R/F1
# ---------------------------------------------------------------------------
def set_metrics(
    y_true_sets: list[list[str]],
    y_pred_sets: list[list[str]],
) -> dict:
    """Micro-averaged P/R/F1 + Jaccard medio sobre conjuntos de tickers."""
    tp = fp = fn = 0
    jaccards: list[float] = []
    exact_matches = 0

    for true, pred in zip(y_true_sets, y_pred_sets):
        s_true = set(t.upper() for t in true)
        s_pred = set(t.upper() for t in pred)

        tp += len(s_true & s_pred)
        fp += len(s_pred - s_true)
        fn += len(s_true - s_pred)

        union = s_true | s_pred
        if not union:
            jaccards.append(1.0)
        else:
            jaccards.append(len(s_true & s_pred) / len(union))

        if s_true == s_pred:
            exact_matches += 1

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    return {
        "n": len(y_true_sets),
        "micro_precision": round(precision, 4),
        "micro_recall": round(recall, 4),
        "micro_f1": round(f1, 4),
        "mean_jaccard": round(sum(jaccards) / len(jaccards), 4) if jaccards else 0.0,
        "exact_match_rate": round(exact_matches / len(y_true_sets), 4) if y_true_sets else 0.0,
    }


# ---------------------------------------------------------------------------
# Ordinal metrics (severity)
# ---------------------------------------------------------------------------
def ordinal_severity_metrics(
    y_true: list[str],
    y_pred: list[str],
) -> dict:
    """MAE sobre la escala ordinal de severidad."""
    idx = {label: i for i, label in enumerate(SEVERITY_ORDER)}
    diffs: list[int] = []
    exact = 0
    one_off = 0

    for t, p in zip(y_true, y_pred):
        if t not in idx or p not in idx:
            continue
        d = abs(idx[t] - idx[p])
        diffs.append(d)
        if d == 0:
            exact += 1
        elif d == 1:
            one_off += 1

    n = len(diffs)
    return {
        "n": n,
        "mae": round(sum(diffs) / n, 4) if n else 0.0,
        "exact_match": round(exact / n, 4) if n else 0.0,
        "off_by_one_or_less": round((exact + one_off) / n, 4) if n else 0.0,
    }


# ---------------------------------------------------------------------------
# Main evaluator
# ---------------------------------------------------------------------------
def evaluate_predictions(
    dataset: list[LabeledNews],
    predictions: list[PipelinePrediction],
) -> dict:
    """
    Empareja dataset y predicciones por `id` y calcula todas las métricas.

    Para etapas posteriores a la relevancia (events, impact), solo se evalúan
    los ejemplos donde tanto el gold como la predicción consideran la noticia
    relevante (de lo contrario el sistema no genera valores comparables).
    """
    pred_by_id = {p.id: p for p in predictions}

    y_rel_true, y_rel_pred = [], []
    matched_true, matched_pred = [], []

    y_event_true, y_event_pred = [], []
    y_dir_true, y_dir_pred = [], []
    y_sev_true, y_sev_pred = [], []

    missing = 0
    for example in dataset:
        pred = pred_by_id.get(example.id)
        if pred is None:
            missing += 1
            continue

        y_rel_true.append(example.labels.is_relevant)
        y_rel_pred.append(pred.is_relevant)

        # matched_assets se evalúa solo cuando el gold dice relevante
        if example.labels.is_relevant:
            matched_true.append(example.labels.matched_assets)
            matched_pred.append(pred.matched_assets)

        # event/direction/severity: solo cuando ambos consideran relevante
        # y el sistema completó las etapas downstream
        if example.labels.is_relevant and pred.is_relevant:
            if pred.event_type is not None:
                y_event_true.append(example.labels.event_type)
                y_event_pred.append(pred.event_type)
            if pred.direction is not None:
                y_dir_true.append(example.labels.direction)
                y_dir_pred.append(pred.direction)
            if pred.severity_label is not None:
                y_sev_true.append(example.labels.severity_label)
                y_sev_pred.append(pred.severity_label)

    return {
        "summary": {
            "dataset_size": len(dataset),
            "predictions_count": len(predictions),
            "missing_predictions": missing,
        },
        "relevance": binary_metrics(y_rel_true, y_rel_pred),
        "matched_assets": set_metrics(matched_true, matched_pred),
        "event_type": multiclass_metrics(y_event_true, y_event_pred),
        "direction": multiclass_metrics(y_dir_true, y_dir_pred, labels=DIRECTION_LABELS),
        "severity": ordinal_severity_metrics(y_sev_true, y_sev_pred),
    }


# ---------------------------------------------------------------------------
# Pretty printer
# ---------------------------------------------------------------------------
def format_report(results: dict, variant: str = "") -> str:
    """Formatea las métricas como tabla legible para terminal/log."""
    lines: list[str] = []
    title = f"=== Evaluación: variante '{variant}' ===" if variant else "=== Evaluación ==="
    lines.append(title)

    s = results["summary"]
    lines.append(
        f"Dataset: {s['dataset_size']} | Predichas: {s['predictions_count']} | "
        f"Faltantes: {s['missing_predictions']}"
    )

    rel = results["relevance"]
    lines.append("\n--- Relevancia (binaria) ---")
    lines.append(
        f"  P={rel['precision']:.3f}  R={rel['recall']:.3f}  F1={rel['f1']:.3f}  "
        f"Acc={rel['accuracy']:.3f}  (TP={rel['confusion_matrix']['tp']} "
        f"FP={rel['confusion_matrix']['fp']} FN={rel['confusion_matrix']['fn']} "
        f"TN={rel['confusion_matrix']['tn']})"
    )

    m = results["matched_assets"]
    lines.append("\n--- Matched assets (micro-avg sobre conjuntos) ---")
    lines.append(
        f"  P={m['micro_precision']:.3f}  R={m['micro_recall']:.3f}  "
        f"F1={m['micro_f1']:.3f}  Jaccard={m['mean_jaccard']:.3f}  "
        f"ExactMatch={m['exact_match_rate']:.3f}"
    )

    e = results["event_type"]
    lines.append("\n--- Tipo de evento (multiclase) ---")
    lines.append(
        f"  Acc={e['accuracy']:.3f}  macroF1={e['macro']['f1']:.3f}  "
        f"weightedF1={e['weighted']['f1']:.3f}  (n={e['n']})"
    )

    d = results["direction"]
    lines.append("\n--- Dirección (alcista/bajista/neutral) ---")
    lines.append(
        f"  Acc={d['accuracy']:.3f}  macroF1={d['macro']['f1']:.3f}  (n={d['n']})"
    )

    sev = results["severity"]
    lines.append("\n--- Severidad (ordinal) ---")
    lines.append(
        f"  MAE={sev['mae']:.3f}  Exact={sev['exact_match']:.3f}  "
        f"±1={sev['off_by_one_or_less']:.3f}  (n={sev['n']})"
    )

    return "\n".join(lines)
