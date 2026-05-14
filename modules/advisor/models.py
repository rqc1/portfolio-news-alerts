"""
Modelos del módulo Advisor – Perfil de inversor, cuestionario y recomendaciones.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums del perfil
# ---------------------------------------------------------------------------
class RiskProfile(str, Enum):
    VERY_CONSERVATIVE = "muy_conservador"
    CONSERVATIVE = "conservador"
    MODERATE = "moderado"
    AGGRESSIVE = "agresivo"
    VERY_AGGRESSIVE = "muy_agresivo"


class InvestmentHorizon(str, Enum):
    SHORT = "corto_plazo"       # < 2 años
    MEDIUM = "medio_plazo"      # 2-7 años
    LONG = "largo_plazo"        # > 7 años


class InvestmentGoal(str, Enum):
    CAPITAL_PRESERVATION = "preservacion_capital"
    INCOME = "generacion_rentas"
    BALANCED_GROWTH = "crecimiento_equilibrado"
    AGGRESSIVE_GROWTH = "crecimiento_agresivo"
    SPECULATION = "especulacion"


class KnowledgeLevel(str, Enum):
    BEGINNER = "principiante"
    INTERMEDIATE = "intermedio"
    ADVANCED = "avanzado"
    EXPERT = "experto"


# ---------------------------------------------------------------------------
# Cuestionario
# ---------------------------------------------------------------------------
class QuestionOption(BaseModel):
    id: str
    text: str
    score: int = Field(..., description="Puntuación para el cálculo del perfil de riesgo")


class Question(BaseModel):
    id: str
    category: str
    text: str
    description: str = ""
    options: list[QuestionOption]


class QuestionnaireAnswer(BaseModel):
    question_id: str
    selected_option_id: str


class QuestionnaireSubmission(BaseModel):
    user_id: str
    portfolio_id: str
    answers: list[QuestionnaireAnswer]


# ---------------------------------------------------------------------------
# Perfil del inversor
# ---------------------------------------------------------------------------
class InvestorProfile(BaseModel):
    user_id: str
    portfolio_id: str
    risk_score: int = Field(..., ge=0, le=100, description="Puntuación de riesgo 0-100")
    risk_profile: RiskProfile
    horizon: InvestmentHorizon
    goal: InvestmentGoal
    knowledge: KnowledgeLevel
    esg_preference: bool = False
    sector_preferences: list[str] = Field(default_factory=list)
    loss_tolerance_pct: float = Field(0.0, description="Pérdida máx. tolerada en % (ej. 20.0)")
    answers_raw: list[QuestionnaireAnswer] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Análisis de cartera
# ---------------------------------------------------------------------------
class AllocationSlice(BaseModel):
    category: str
    current_pct: float = Field(..., description="% actual en la cartera")
    ideal_pct: float = Field(..., description="% ideal según perfil")
    diff_pct: float = Field(..., description="Desviación (current - ideal)")
    status: str = Field(..., description="sobreexpuesto | infraexpuesto | equilibrado")


class PortfolioAnalysis(BaseModel):
    concentration_risk: float = Field(..., description="HHI de concentración 0-1")
    sector_allocation: list[AllocationSlice]
    geography_allocation: list[AllocationSlice]
    diversification_score: float = Field(..., ge=0, le=100)
    risk_alignment_score: float = Field(..., ge=0, le=100,
                                        description="Qué tan bien encaja la cartera con el perfil")
    warnings: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Recomendaciones
# ---------------------------------------------------------------------------
class Recommendation(BaseModel):
    action: str = Field(..., description="comprar | vender | reducir | aumentar | mantener")
    ticker: Optional[str] = None
    asset_name: str = ""
    sector: str = ""
    reason: str = ""
    priority: str = Field("media", description="alta | media | baja")
    current_weight: Optional[float] = None
    suggested_weight: Optional[float] = None


class AdvisorReport(BaseModel):
    profile: InvestorProfile
    analysis: PortfolioAnalysis
    recommendations: list[Recommendation]
    llm_summary: str = Field("", description="Análisis detallado generado por LLM")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
