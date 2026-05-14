"""
Schema de etiquetado del corpus de evaluación.

Cada ejemplo (`LabeledNews`) representa una noticia anotada manualmente con:
  - Texto + metadatos de origen
  - Etiquetas gold (ground truth) para cada etapa del pipeline
  - Cartera de referencia (`portfolio_id`) sobre la que se evalúa la relevancia

Las predicciones del sistema (`PipelinePrediction`) se generan en `runner.py`
y se comparan con las etiquetas gold en `metrics.py`.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Etiquetas gold
# ---------------------------------------------------------------------------
Direction = Literal["alcista", "bajista", "neutral"]
SeverityLabel = Literal["muy_baja", "baja", "media", "alta", "muy_alta"]


class GoldLabels(BaseModel):
    """Anotación manual (ground truth) de una noticia."""
    is_relevant: bool = Field(..., description="¿La noticia es relevante para la cartera?")
    matched_assets: list[str] = Field(
        default_factory=list,
        description="Tickers de la cartera afectados (gold)",
    )
    event_type: str = Field(..., description="Tipo de evento de la taxonomía EVENT_TAXONOMY")
    direction: Direction = Field(..., description="Dirección esperada del impacto")
    severity_label: SeverityLabel = Field(..., description="Severidad cualitativa esperada")


class LabeledNews(BaseModel):
    """Una noticia anotada del corpus de evaluación."""
    id: str = Field(..., description="Identificador único del ejemplo")
    portfolio_id: str = Field(..., description="ID de la cartera de referencia")
    title: str
    summary: str = ""
    content: str = ""
    url: str = ""
    source: str = "eval"
    language: str = "en"
    labels: GoldLabels


class PortfolioFixture(BaseModel):
    """Cartera de referencia para evaluación (no se persiste en MongoDB)."""
    portfolio_id: str
    name: str
    assets: list[dict]


# ---------------------------------------------------------------------------
# Predicción del sistema
# ---------------------------------------------------------------------------
class PipelinePrediction(BaseModel):
    """Salida del pipeline para un ejemplo."""
    id: str
    portfolio_id: str

    # Etapa relevancia
    is_relevant: bool
    relevance_score: float
    matched_assets: list[str] = Field(default_factory=list)
    direct_score: float = 0.0
    semantic_score: float = 0.0

    # Etapa eventos
    event_type: Optional[str] = None
    event_confidence: float = 0.0
    sentiment: Optional[str] = None
    sentiment_confidence: float = 0.0

    # Etapa impacto
    direction: Optional[Direction] = None
    severity: float = 0.0
    severity_label: Optional[SeverityLabel] = None
    confidence: float = 0.0

    # Variante usada (para ablation)
    variant: str = "full"
    # Si la noticia fue descartada antes de llegar al final
    discarded_at: Optional[str] = None
