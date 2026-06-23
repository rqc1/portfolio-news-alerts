"""
Calibración empírica de severidad.

El problema: la severidad estimada (0–1) es una magnitud abstracta sin anclaje
en la realidad financiera, y el LLM la sobrescribía libremente, degradando la
precisión (MAE) frente al estimador determinista.

Solución:
  1. Anclar la severidad a una magnitud observable: el retorno anormal
     acumulado absoluto |CAR| medido por el estudio de eventos.
  2. Definir bandas de severidad (etiquetas) sobre rangos concretos de |CAR|,
     derivadas de la literatura y refinables empíricamente.
  3. Ajustar (opcionalmente) una regresión isotónica monótona
     severidad → E[|CAR|] a partir de los resultados de backtesting, de modo
     que las estimaciones futuras estén calibradas con datos reales.

La calibración es persistible (JSON) y degrada con elegancia: sin datos de
ajuste utiliza las bandas teóricas por defecto.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


# Bandas teóricas por defecto: etiqueta -> (|CAR| mínimo, |CAR| máximo).
# Basadas en magnitudes habituales de retorno anormal en estudios de eventos
# sobre noticias corporativas (Campbell, Lo y MacKinlay, 1997).
DEFAULT_SEVERITY_BANDS: dict[str, tuple[float, float]] = {
    "muy_baja": (0.000, 0.005),   # < 0.5%
    "baja":     (0.005, 0.015),   # 0.5% – 1.5%
    "media":    (0.015, 0.030),   # 1.5% – 3%
    "alta":     (0.030, 0.060),   # 3% – 6%
    "muy_alta": (0.060, 1.000),   # > 6%
}

# Orden ordinal de las etiquetas.
SEVERITY_ORDER = ["muy_baja", "baja", "media", "alta", "muy_alta"]

# Umbrales del score de severidad (0–1) para cada etiqueta.
# Coinciden con _severity_label del estimador para mantener coherencia.
SCORE_THRESHOLDS: list[tuple[float, str]] = [
    (0.8, "muy_alta"),
    (0.6, "alta"),
    (0.4, "media"),
    (0.2, "baja"),
    (0.0, "muy_baja"),
]


def severity_score_to_label(score: float) -> str:
    for threshold, label in SCORE_THRESHOLDS:
        if score >= threshold:
            return label
    return "muy_baja"


def label_to_expected_abs_car(label: str) -> float:
    """Punto medio del rango de |CAR| de la banda (valor esperado teórico)."""
    lo, hi = DEFAULT_SEVERITY_BANDS.get(label, (0.0, 0.005))
    # Para la banda abierta superior usamos un valor representativo acotado.
    hi = min(hi, 0.12)
    return (lo + hi) / 2.0


def abs_car_to_label(abs_car: float) -> str:
    """Mapea un |CAR| observado a la etiqueta de severidad correspondiente."""
    for label in SEVERITY_ORDER:
        lo, hi = DEFAULT_SEVERITY_BANDS[label]
        if lo <= abs_car < hi:
            return label
    return "muy_alta"


@dataclass
class SeverityCalibrator:
    """Mapeo monótono severidad(0–1) → E[|CAR|] ajustable empíricamente."""

    # Puntos de la curva isotónica ajustada (x=score, y=E[|CAR|]).
    x_points: Optional[list[float]] = None
    y_points: Optional[list[float]] = None
    n_samples: int = 0
    fitted: bool = False

    def expected_abs_car(self, score: float) -> float:
        """Devuelve el |CAR| esperado para un score de severidad dado."""
        if self.fitted and self.x_points and self.y_points:
            return float(np.interp(score, self.x_points, self.y_points))
        # Fallback teórico: interpolar a partir de las bandas por etiqueta.
        return label_to_expected_abs_car(severity_score_to_label(score))

    def fit(self, scores: list[float], abs_cars: list[float], min_samples: int = 15) -> bool:
        """Ajusta una regresión isotónica monótona creciente.

        Requiere al menos `min_samples` pares. Devuelve True si se ajustó.
        """
        if len(scores) < min_samples or len(scores) != len(abs_cars):
            logger.info(
                "Calibración omitida: %d muestras (<%d requeridas)",
                len(scores), min_samples,
            )
            return False
        try:
            from sklearn.isotonic import IsotonicRegression

            iso = IsotonicRegression(
                y_min=0.0, out_of_bounds="clip", increasing=True
            )
            x = np.asarray(scores, dtype="float64")
            y = np.asarray(abs_cars, dtype="float64")
            iso.fit(x, y)
            grid = np.linspace(0.0, 1.0, 21)
            self.x_points = grid.tolist()
            self.y_points = [float(v) for v in iso.predict(grid)]
            self.n_samples = len(scores)
            self.fitted = True
            logger.info("Calibrador de severidad ajustado con %d muestras", self.n_samples)
            return True
        except Exception as exc:  # pragma: no cover
            logger.warning("Fallo al ajustar el calibrador: %s", exc)
            return False

    def to_dict(self) -> dict:
        return {
            "fitted": self.fitted,
            "n_samples": self.n_samples,
            "x_points": self.x_points,
            "y_points": self.y_points,
        }

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "SeverityCalibrator":
        p = Path(path)
        if not p.exists():
            return cls()
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            return cls(
                x_points=data.get("x_points"),
                y_points=data.get("y_points"),
                n_samples=data.get("n_samples", 0),
                fitted=data.get("fitted", False),
            )
        except Exception:  # pragma: no cover
            return cls()
