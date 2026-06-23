"""Tests del módulo de acuerdo inter-anotador (evaluation/agreement.py)."""

import math

from evaluation.agreement import (
    agreement_report,
    cohen_kappa,
    fleiss_kappa,
    interpret_kappa,
    krippendorff_alpha,
    percentage_agreement,
    weighted_cohen_kappa,
)

SEV = ["muy_baja", "baja", "media", "alta", "muy_alta"]


class TestPercentage:
    def test_perfect(self):
        assert percentage_agreement(["a", "b", "c"], ["a", "b", "c"]) == 1.0

    def test_half(self):
        assert percentage_agreement(["a", "b"], ["a", "x"]) == 0.5

    def test_empty(self):
        assert percentage_agreement([], []) == 0.0


class TestCohen:
    def test_perfect_agreement(self):
        a = ["alcista", "bajista", "neutral", "alcista"]
        assert cohen_kappa(a, a) == 1.0

    def test_known_value(self):
        # Ejemplo clásico (Wikipedia Cohen's kappa): κ = 0.4.
        # 2 categorías Yes/No, 50 ítems.
        a = ["y"] * 20 + ["y"] * 5 + ["n"] * 10 + ["n"] * 15
        b = ["y"] * 20 + ["n"] * 5 + ["y"] * 10 + ["n"] * 15
        assert math.isclose(cohen_kappa(a, b), 0.4, abs_tol=1e-9)

    def test_single_category(self):
        assert cohen_kappa(["x", "x"], ["x", "x"]) == 1.0

    def test_no_better_than_chance(self):
        # Etiquetas independientes equilibradas → κ ≈ 0.
        a = ["a", "b", "a", "b"]
        b = ["a", "a", "b", "b"]
        assert math.isclose(cohen_kappa(a, b), 0.0, abs_tol=1e-9)


class TestWeightedKappa:
    def test_perfect(self):
        a = ["baja", "alta", "media"]
        assert weighted_cohen_kappa(a, a, SEV) == 1.0

    def test_ordinal_penalizes_less_close(self):
        # Desacuerdo entre categorías adyacentes da κ ponderado mayor que el
        # κ nominal (que sería más bajo).
        a = ["baja", "media", "alta", "muy_alta"]
        b = ["media", "alta", "muy_alta", "muy_alta"]
        wk = weighted_cohen_kappa(a, b, SEV, weights="quadratic")
        nominal = cohen_kappa(a, b)
        assert wk > nominal


class TestFleiss:
    def test_perfect(self):
        ratings = [["a", "a", "a"], ["b", "b", "b"]]
        assert fleiss_kappa(ratings) == 1.0

    def test_partial(self):
        ratings = [["a", "a", "b"], ["b", "b", "b"], ["a", "b", "a"]]
        k = fleiss_kappa(ratings)
        assert -1.0 <= k <= 1.0


class TestKrippendorff:
    def test_perfect_nominal(self):
        ann = [["a", "b", "c"], ["a", "b", "c"]]
        assert krippendorff_alpha(ann, level="nominal") == 1.0

    def test_ordinal_with_missing(self):
        ann = [
            ["baja", "media", None, "alta"],
            ["baja", "media", "alta", "alta"],
        ]
        alpha = krippendorff_alpha(ann, level="ordinal", categories=SEV)
        assert 0.0 < alpha <= 1.0

    def test_disagreement_low_alpha(self):
        ann = [["a", "b", "a", "b"], ["b", "a", "b", "a"]]
        alpha = krippendorff_alpha(ann, level="nominal")
        assert alpha < 0.2


class TestInterpret:
    def test_bands(self):
        assert interpret_kappa(-0.1) == "pobre"
        assert interpret_kappa(0.1) == "leve"
        assert interpret_kappa(0.3) == "aceptable"
        assert interpret_kappa(0.5) == "moderado"
        assert interpret_kappa(0.7) == "sustancial"
        assert interpret_kappa(0.9) == "casi_perfecto"


class TestReport:
    def test_report_structure(self):
        a = {
            "ev001": {"is_relevant": True, "event_type": "resultados",
                      "direction": "alcista", "severity_label": "alta"},
            "ev002": {"is_relevant": True, "event_type": "regulacion",
                      "direction": "bajista", "severity_label": "media"},
        }
        b = {
            "ev001": {"is_relevant": True, "event_type": "resultados",
                      "direction": "alcista", "severity_label": "alta"},
            "ev002": {"is_relevant": False, "event_type": "regulacion",
                      "direction": "bajista", "severity_label": "baja"},
        }
        rep = agreement_report(a, b)
        assert rep["n_common_items"] == 2
        assert "is_relevant" in rep["dimensions"]
        assert "severity_label" in rep["dimensions"]
        sev = rep["dimensions"]["severity_label"]
        assert "weighted_cohen_kappa_quadratic" in sev
        assert "krippendorff_alpha_ordinal" in sev
