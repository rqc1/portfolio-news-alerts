"""
Módulo 7 – Motor de alertas.

Orquesta todo el pipeline: NLP → Relevancia → Eventos → Impacto → Alerta.
Incluye anti-spam, deduplicación semántica y generación explicable.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field

import config
from database.mongodb import MongoDB
from modules.portfolio.models import Portfolio
from modules.nlp.preprocessing import NLPService
from modules.relevance.service import RelevanceService
from modules.events.classifier import EventClassificationService
from modules.impact.estimator import ImpactEstimator
from modules.alerts.deduplication import SemanticDeduplicator
from modules.alerts.explainer import AlertExplainer

logger = logging.getLogger(__name__)


class Alert(BaseModel):
    news_id: str = ""
    news_title: str
    news_url: str = ""
    news_source: str = ""
    portfolio_id: str = ""

    matched_assets: list[str] = Field(default_factory=list)
    event_type: str
    direction: str
    severity: float
    severity_label: str
    confidence: float
    relevance_score: float

    sentiment: str
    sentiment_confidence: float

    explanation: str

    is_duplicate: bool = False
    duplicate_similarity: float = 0.0

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AlertEngine:
    """Motor principal de alertas. Procesa noticias y genera alertas explicables."""

    def __init__(self):
        self.nlp_service = NLPService()
        self.relevance_service = RelevanceService()
        self.event_service = EventClassificationService()
        self.deduplicator = SemanticDeduplicator()
        self._alerts_this_hour = 0
        self._hour_start: Optional[datetime] = None

    def process_news(
        self,
        title: str,
        summary: str,
        content: str,
        url: str,
        source: str,
        portfolio: Portfolio,
        news_id: str = "",
    ) -> Optional[Alert]:
        """
        Pipeline completo: noticia → alerta (o None si no es relevante).
        """
        # --- Anti-spam: limitar alertas por hora ---
        now = datetime.now(timezone.utc)
        if self._hour_start is None or (now - self._hour_start).total_seconds() > 3600:
            self._hour_start = now
            self._alerts_this_hour = 0

        if self._alerts_this_hour >= config.ALERT_MAX_PER_HOUR:
            logger.warning("Rate limit: max alerts per hour reached")
            return None

        # --- Paso 1: Preprocesado NLP ---
        nlp_result = self.nlp_service.process(title, summary, content)
        cleaned_text = nlp_result["cleaned_text"]
        org_names = nlp_result["org_names"]

        # --- Paso 2: Relevancia por cartera ---
        relevance = self.relevance_service.compute_relevance(
            cleaned_text, org_names, portfolio
        )

        if relevance["relevance_score"] < config.ALERT_RELEVANCE_THRESHOLD:
            logger.debug("Noticia descartada por baja relevancia: %.3f", relevance["relevance_score"])
            return None

        # --- Paso 3: Clasificación de evento ---
        event_result = self.event_service.classify(cleaned_text)

        # --- Paso 4: Estimación de impacto ---
        impact = ImpactEstimator.estimate(
            sentiment=event_result["sentiment"],
            event_type=event_result["event_type"],
            event_confidence=event_result["event_confidence"],
            relevance_score=relevance["relevance_score"],
            matched_assets=relevance["matched_assets"],
        )

        if impact["severity"] < config.ALERT_SEVERITY_THRESHOLD:
            logger.debug("Noticia descartada por baja severidad: %.3f", impact["severity"])
            return None

        # --- Paso 5: Deduplicación semántica ---
        is_dup, dup_sim = self.deduplicator.is_duplicate(cleaned_text, news_id)

        # --- Paso 6: Generación de explicación ---
        explanation = AlertExplainer.generate(
            title=title,
            matched_assets=relevance["matched_assets"],
            event_type=event_result["event_type"],
            direction=impact["direction"],
            severity_label=impact["severity_label"],
            confidence=impact["confidence"],
            relevance_score=relevance["relevance_score"],
            source=source,
            sentiment=event_result["sentiment"]["sentiment"],
        )

        alert = Alert(
            news_id=news_id,
            news_title=title,
            news_url=url,
            news_source=source,
            matched_assets=relevance["matched_assets"],
            event_type=event_result["event_type"],
            direction=impact["direction"],
            severity=impact["severity"],
            severity_label=impact["severity_label"],
            confidence=impact["confidence"],
            relevance_score=relevance["relevance_score"],
            sentiment=event_result["sentiment"]["sentiment"],
            sentiment_confidence=event_result["sentiment"]["confidence"],
            explanation=explanation,
            is_duplicate=is_dup,
            duplicate_similarity=dup_sim,
        )

        if not is_dup:
            self._alerts_this_hour += 1

        return alert

    async def process_and_store(
        self,
        title: str,
        summary: str,
        content: str,
        url: str,
        source: str,
        portfolio: Portfolio,
        portfolio_id: str = "",
        news_id: str = "",
    ) -> Optional[Alert]:
        """Procesa una noticia y almacena la alerta en MongoDB si procede."""
        alert = self.process_news(
            title=title,
            summary=summary,
            content=content,
            url=url,
            source=source,
            portfolio=portfolio,
            news_id=news_id,
        )

        if alert and not alert.is_duplicate:
            alert.portfolio_id = portfolio_id
            doc = alert.model_dump()
            await MongoDB.alerts().insert_one(doc)
            logger.info("Alert stored: %s [%s] %s", alert.direction, alert.event_type, title[:80])

        return alert
