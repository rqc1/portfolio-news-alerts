"""Tests del calibrador de severidad (modules/impact/calibration.py)."""

import numpy as np

from modules.impact.calibration import (
    DEFAULT_SEVERITY_BANDS,
    SeverityCalibrator,
    abs_car_to_label,
    label_to_expected_abs_car,
    severity_score_to_label,
)


class TestBands:
    def test_score_to_label_monotone(self):
        assert severity_score_to_label(0.9) == "muy_alta"
        assert severity_score_to_label(0.65) == "alta"
        assert severity_score_to_label(0.45) == "media"
        assert severity_score_to_label(0.25) == "baja"
        assert severity_score_to_label(0.05) == "muy_baja"

    def test_abs_car_to_label(self):
        assert abs_car_to_label(0.001) == "muy_baja"
        assert abs_car_to_label(0.01) == "baja"
        assert abs_car_to_label(0.02) == "media"
        assert abs_car_to_label(0.05) == "alta"
        assert abs_car_to_label(0.10) == "muy_alta"

    def test_expected_abs_car_increases_with_label(self):
        vals = [label_to_expected_abs_car(l) for l in
                ["muy_baja", "baja", "media", "alta", "muy_alta"]]
        assert all(vals[i] < vals[i + 1] for i in range(len(vals) - 1))

    def test_bands_cover_unit_interval(self):
        # Las bandas son contiguas y cubren [0,1].
        ordered = [DEFAULT_SEVERITY_BANDS[l] for l in
                   ["muy_baja", "baja", "media", "alta", "muy_alta"]]
        for (lo1, hi1), (lo2, hi2) in zip(ordered, ordered[1:]):
            assert hi1 == lo2


class TestCalibrator:
    def test_fallback_without_fit(self):
        cal = SeverityCalibrator()
        assert not cal.fitted
        # Usa bandas teóricas.
        assert cal.expected_abs_car(0.9) > cal.expected_abs_car(0.1)

    def test_fit_monotone(self):
        rng = np.random.default_rng(0)
        scores = rng.uniform(0, 1, 100).tolist()
        # |CAR| crece con el score + ruido.
        abs_cars = [0.08 * s + abs(rng.normal(0, 0.005)) for s in scores]
        cal = SeverityCalibrator()
        assert cal.fit(scores, abs_cars)
        assert cal.fitted
        # Monotonía: mayor score -> mayor |CAR| esperado.
        assert cal.expected_abs_car(0.9) >= cal.expected_abs_car(0.2)

    def test_fit_too_few_samples(self):
        cal = SeverityCalibrator()
        assert not cal.fit([0.1, 0.2], [0.01, 0.02])
        assert not cal.fitted

    def test_save_load(self, tmp_path):
        rng = np.random.default_rng(1)
        scores = rng.uniform(0, 1, 50).tolist()
        abs_cars = [0.06 * s for s in scores]
        cal = SeverityCalibrator()
        cal.fit(scores, abs_cars)
        p = tmp_path / "cal.json"
        cal.save(p)
        loaded = SeverityCalibrator.load(p)
        assert loaded.fitted
        assert loaded.expected_abs_car(0.5) == cal.expected_abs_car(0.5)

    def test_load_missing_file(self, tmp_path):
        cal = SeverityCalibrator.load(tmp_path / "nope.json")
        assert not cal.fitted
