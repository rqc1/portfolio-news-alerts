"""Tests del servicio de backtesting y del cierre del bucle de feedback."""

from datetime import date, datetime

from modules.backtest.service import AlertBacktestService
from modules.impact.calibration import SeverityCalibrator


class TestEventDate:
    def test_datetime(self):
        d = AlertBacktestService._event_date({"created_at": datetime(2025, 3, 1, 12, 0)})
        assert d == date(2025, 3, 1)

    def test_iso_string_z(self):
        d = AlertBacktestService._event_date({"created_at": "2025-03-01T12:00:00Z"})
        assert d == date(2025, 3, 1)

    def test_invalid_string(self):
        assert AlertBacktestService._event_date({"created_at": "not-a-date"}) is None

    def test_missing(self):
        assert AlertBacktestService._event_date({}) is None


class TestEstimatorCalibrationLoop:
    """El estimador debe usar el calibrador empírico cuando existe el fichero."""

    def test_no_calibrator_no_extra_fields(self, tmp_path, monkeypatch):
        import config
        from modules.impact import estimator as est_mod

        # Apuntar a un fichero inexistente → comportamiento por defecto.
        monkeypatch.setattr(config, "SEVERITY_CALIBRATOR_PATH",
                            str(tmp_path / "missing.json"), raising=False)
        est_mod._CALIBRATOR_CACHE.update({"path": None, "mtime": None, "obj": None})

        out = est_mod.ImpactEstimator.estimate(
            sentiment={"sentiment": "negative", "confidence": 0.9},
            event_type="ciberincidente",
            event_confidence=0.8,
            relevance_score=0.9,
            matched_assets=["AAPL"],
        )
        assert "severity_label_calibrated" not in out
        assert "severity_label" in out

    def test_with_calibrator_adds_calibrated_label(self, tmp_path, monkeypatch):
        import config
        from modules.impact import estimator as est_mod

        # Ajustar y guardar un calibrador con datos sintéticos monótonos.
        scores = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9,
                  0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85]
        abs_cars = [0.002, 0.006, 0.012, 0.02, 0.03, 0.045, 0.06, 0.08, 0.1,
                    0.004, 0.009, 0.015, 0.025, 0.04, 0.05, 0.07, 0.09]
        cal = SeverityCalibrator()
        assert cal.fit(scores, abs_cars)
        path = tmp_path / "cal.json"
        cal.save(str(path))

        monkeypatch.setattr(config, "SEVERITY_CALIBRATOR_PATH", str(path), raising=False)
        est_mod._CALIBRATOR_CACHE.update({"path": None, "mtime": None, "obj": None})

        out = est_mod.ImpactEstimator.estimate(
            sentiment={"sentiment": "negative", "confidence": 0.9},
            event_type="ciberincidente",
            event_confidence=0.8,
            relevance_score=0.9,
            matched_assets=["AAPL"],
        )
        assert "severity_label_calibrated" in out
        assert "expected_abs_car" in out
        assert out["expected_abs_car"] >= 0.0
