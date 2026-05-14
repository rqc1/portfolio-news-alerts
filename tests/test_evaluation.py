"""Tests del módulo de evaluación: schema, métricas, carga del corpus."""

from pathlib import Path

import pytest

from evaluation import metrics
from evaluation.runner import load_dataset, load_portfolios
from evaluation.schema import GoldLabels, LabeledNews, PipelinePrediction


# ---------------------------------------------------------------------------
# Métricas binarias
# ---------------------------------------------------------------------------
def test_binary_metrics_perfect():
    res = metrics.binary_metrics([True, False, True, False], [True, False, True, False])
    assert res["precision"] == 1.0
    assert res["recall"] == 1.0
    assert res["f1"] == 1.0
    assert res["accuracy"] == 1.0
    assert res["confusion_matrix"] == {"tp": 2, "fp": 0, "fn": 0, "tn": 2}


def test_binary_metrics_mixed():
    res = metrics.binary_metrics(
        [True, True, False, False, True],
        [True, False, True, False, True],
    )
    # tp=2, fp=1, fn=1, tn=1
    assert res["confusion_matrix"] == {"tp": 2, "fp": 1, "fn": 1, "tn": 1}
    assert res["precision"] == round(2 / 3, 4)
    assert res["recall"] == round(2 / 3, 4)


def test_binary_metrics_empty():
    res = metrics.binary_metrics([], [])
    assert res["precision"] == 0.0
    assert res["accuracy"] == 0.0


# ---------------------------------------------------------------------------
# Métricas multiclase
# ---------------------------------------------------------------------------
def test_multiclass_metrics_basic():
    y_true = ["a", "b", "a", "c", "b"]
    y_pred = ["a", "b", "b", "c", "b"]
    res = metrics.multiclass_metrics(y_true, y_pred)
    assert res["accuracy"] == 0.8
    assert "a" in res["per_class"]
    assert res["per_class"]["a"]["support"] == 2


def test_multiclass_metrics_with_labels():
    res = metrics.multiclass_metrics(
        ["alcista", "bajista"],
        ["alcista", "neutral"],
        labels=["alcista", "bajista", "neutral"],
    )
    assert set(res["per_class"].keys()) == {"alcista", "bajista", "neutral"}


# ---------------------------------------------------------------------------
# Set metrics (matched assets)
# ---------------------------------------------------------------------------
def test_set_metrics_perfect():
    res = metrics.set_metrics(
        [["AAPL"], ["MSFT", "NVDA"]],
        [["AAPL"], ["MSFT", "NVDA"]],
    )
    assert res["micro_f1"] == 1.0
    assert res["mean_jaccard"] == 1.0
    assert res["exact_match_rate"] == 1.0


def test_set_metrics_partial():
    # tp=1 (AAPL), fp=1 (MSFT predicho de más), fn=1 (NVDA no predicho)
    res = metrics.set_metrics(
        [["AAPL", "NVDA"]],
        [["AAPL", "MSFT"]],
    )
    assert res["micro_precision"] == 0.5
    assert res["micro_recall"] == 0.5
    assert res["mean_jaccard"] == round(1 / 3, 4)


def test_set_metrics_empty_sets():
    # Ambos vacíos → Jaccard convencional 1.0 (no hay desacuerdo)
    res = metrics.set_metrics([[]], [[]])
    assert res["mean_jaccard"] == 1.0


# ---------------------------------------------------------------------------
# Métricas ordinales (severidad)
# ---------------------------------------------------------------------------
def test_severity_mae_exact():
    res = metrics.ordinal_severity_metrics(
        ["alta", "media"],
        ["alta", "media"],
    )
    assert res["mae"] == 0.0
    assert res["exact_match"] == 1.0


def test_severity_mae_off_by_one():
    # alta(3) vs muy_alta(4) -> diff 1; media(2) vs baja(1) -> diff 1
    res = metrics.ordinal_severity_metrics(
        ["alta", "media"],
        ["muy_alta", "baja"],
    )
    assert res["mae"] == 1.0
    assert res["off_by_one_or_less"] == 1.0
    assert res["exact_match"] == 0.0


# ---------------------------------------------------------------------------
# Pipeline integrado (sin ML — usamos predicciones sintéticas)
# ---------------------------------------------------------------------------
def _make_example(eid: str, is_relevant: bool, event="otro",
                  direction="neutral", severity="muy_baja",
                  matched=None) -> LabeledNews:
    return LabeledNews(
        id=eid,
        portfolio_id="p1",
        title="t",
        labels=GoldLabels(
            is_relevant=is_relevant,
            matched_assets=matched or [],
            event_type=event,
            direction=direction,
            severity_label=severity,
        ),
    )


def _make_pred(eid: str, is_relevant: bool, event=None,
               direction=None, severity=None, matched=None) -> PipelinePrediction:
    return PipelinePrediction(
        id=eid,
        portfolio_id="p1",
        is_relevant=is_relevant,
        relevance_score=0.9 if is_relevant else 0.1,
        matched_assets=matched or [],
        event_type=event,
        direction=direction,
        severity_label=severity,
    )


def test_evaluate_predictions_full():
    dataset = [
        _make_example("a", True, "resultados_empresariales", "alcista", "alta", ["AAPL"]),
        _make_example("b", False),
        _make_example("c", True, "regulacion", "bajista", "media", ["MSFT"]),
    ]
    predictions = [
        _make_pred("a", True, "resultados_empresariales", "alcista", "alta", ["AAPL"]),
        _make_pred("b", False),
        _make_pred("c", True, "litigio", "bajista", "alta", ["MSFT"]),
    ]
    res = metrics.evaluate_predictions(dataset, predictions)
    assert res["summary"]["dataset_size"] == 3
    assert res["summary"]["missing_predictions"] == 0
    assert res["relevance"]["precision"] == 1.0
    assert res["relevance"]["recall"] == 1.0
    # Event type: 1/2 correcto
    assert res["event_type"]["accuracy"] == 0.5
    # Severity off-by-one en ejemplo c (media→alta)
    assert res["severity"]["off_by_one_or_less"] == 1.0


def test_evaluate_predictions_with_missing():
    dataset = [_make_example("a", True), _make_example("b", True)]
    predictions = [_make_pred("a", True)]
    res = metrics.evaluate_predictions(dataset, predictions)
    assert res["summary"]["missing_predictions"] == 1


# ---------------------------------------------------------------------------
# Carga del corpus seed
# ---------------------------------------------------------------------------
def test_load_seed_dataset():
    dataset = load_dataset()
    assert len(dataset) >= 30, f"Dataset semilla demasiado pequeño: {len(dataset)}"
    # Balance mínimo: al menos 5 ejemplos no relevantes (negativos)
    negatives = sum(1 for e in dataset if not e.labels.is_relevant)
    assert negatives >= 4, f"Faltan ejemplos negativos: {negatives}"
    # Cobertura de la taxonomía: al menos 6 tipos distintos
    event_types = {e.labels.event_type for e in dataset if e.labels.is_relevant}
    assert len(event_types) >= 6, f"Cobertura de eventos baja: {event_types}"


def test_load_portfolios():
    portfolios = load_portfolios()
    assert "tech_us" in portfolios
    assert "iberico_diversificado" in portfolios
    assert "energia_global" in portfolios
    # Todos los portfolio_id del dataset deben existir
    dataset = load_dataset()
    for example in dataset:
        assert example.portfolio_id in portfolios, (
            f"Cartera {example.portfolio_id} referenciada por {example.id} no existe"
        )


def test_dataset_labels_consistency():
    """Si is_relevant=False, no debería haber matched_assets."""
    dataset = load_dataset()
    for example in dataset:
        if not example.labels.is_relevant:
            assert example.labels.matched_assets == [], (
                f"Ejemplo {example.id}: marcado no-relevante pero tiene matched_assets"
            )


def test_format_report_runs():
    """El formateador no debe romper con métricas válidas."""
    dataset = [_make_example("a", True, matched=["AAPL"])]
    predictions = [_make_pred("a", True, matched=["AAPL"])]
    res = metrics.evaluate_predictions(dataset, predictions)
    text = metrics.format_report(res, variant="test")
    assert "Evaluación" in text
    assert "Relevancia" in text
