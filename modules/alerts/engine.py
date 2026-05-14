"""
Módulo 7 – Motor de alertas.

Orquesta todo el pipeline: NLP → Relevancia (+ LLM borderline) → Eventos (NLI)
→ Impacto determinista → Análisis contextual LLM → Alerta explicable.

Incluye anti-spam, deduplicación semántica y generación de explicaciones
contextualizadas a la cartera del usuario.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field

import config
from database.mongodb import MongoDB
from modules.portfolio.models import Portfolio
from modules.impact.estimator import ImpactEstimator
from modules.alerts.explainer import AlertExplainer
from modules.llm.analyzer import ContextualAnalyzer, RelevanceChecker
from modules.notifications.service import NotificationService

# Cloud mode: importar servicios ligeros (LLM-only, sin modelos locales)
if config.CLOUD_MODE:
    from modules.cloud_mode import CloudRelevanceService, CloudEventClassificationService
else:
    from modules.nlp.preprocessing import NLPService
    from modules.relevance.service import RelevanceService
    from modules.events.classifier import EventClassificationService
    from modules.alerts.deduplication import SemanticDeduplicator

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
    """
    Motor principal de alertas.

    Pipeline:
      1. NLP preprocessing (limpieza, NER, detección de idioma)
      2. Relevancia por cartera (reglas + semántica)
         2b. Si borderline → LLM decide relevancia indirecta
      3. Clasificación de evento (FinBERT sentiment + zero-shot NLI)
      4. Estimación de impacto determinista (priors + heurísticas)
      5. Análisis contextual LLM (sobreescribe impacto + genera explicación)
      6. Deduplicación semántica
      7. Generación de explicación (LLM si disponible, template si no)
    """

    def __init__(self):
        self.cloud_mode = config.CLOUD_MODE
        if self.cloud_mode:
            from modules.cloud_mode import CloudNLPService
            self.nlp_service = CloudNLPService()
            self.relevance_service = CloudRelevanceService()
            self.event_service = CloudEventClassificationService()
            self.deduplicator = None  # Skip dedup in cloud mode (needs embeddings)
        else:
            self.nlp_service = NLPService()
            self.relevance_service = RelevanceService()
            self.event_service = EventClassificationService()
            self.deduplicator = SemanticDeduplicator()
        self.contextual_analyzer = ContextualAnalyzer()
        self.relevance_checker = RelevanceChecker()
        self._alerts_this_hour = 0
        self._hour_start: Optional[datetime] = None

    async def process_news(
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
        # Usar texto traducido al inglés para modelos NLP (FinBERT, NLI)
        cleaned_text_en = nlp_result.get("cleaned_text_en", cleaned_text)
        org_names = nlp_result["org_names"]

        # --- Paso 2: Relevancia por cartera ---
        if self.cloud_mode:
            relevance = await self.relevance_service.compute_relevance(
                cleaned_text, org_names, portfolio
            )
        else:
            relevance = self.relevance_service.compute_relevance(
                cleaned_text, org_names, portfolio
            )

        relevance_score = relevance["relevance_score"]
        matched_assets = relevance["matched_assets"]

        # --- Paso 2b: Filtro de relevancia con LLM para zona borderline ---
        if relevance_score < config.ALERT_RELEVANCE_THRESHOLD:
            if relevance_score >= config.ALERT_RELEVANCE_BORDERLINE:
                # Zona borderline: dejar que el LLM decida
                llm_relevance = await self.relevance_checker.check(title, summary, portfolio)
                if llm_relevance and llm_relevance["is_relevant"]:
                    relevance_score = max(
                        relevance_score,
                        llm_relevance["relevance_score"],
                    )
                    # Incorporar assets detectados por el LLM
                    for asset in llm_relevance.get("affected_assets", []):
                        if asset not in matched_assets:
                            matched_assets.append(asset)
                    logger.info(
                        "LLM rescató noticia borderline: score %.3f → %.3f, razón: %s",
                        relevance["relevance_score"],
                        relevance_score,
                        llm_relevance.get("reason", ""),
                    )
                else:
                    logger.debug("Noticia borderline descartada por LLM")
                    return None
            else:
                logger.debug("Noticia descartada por baja relevancia: %.3f", relevance_score)
                return None

        # Verificar umbral final
        if relevance_score < config.ALERT_RELEVANCE_BORDERLINE:
            return None

        # --- Paso 3: Clasificación de evento (NLI local + FinBERT / LLM en cloud) ---
        if self.cloud_mode:
            event_result = await self.event_service.classify(cleaned_text_en)
        else:
            event_result = self.event_service.classify(cleaned_text_en)

        # --- Paso 4: Estimación de impacto determinista (pre-filtro rápido) ---
        impact_deterministic = ImpactEstimator.estimate(
            sentiment=event_result["sentiment"],
            event_type=event_result["event_type"],
            event_confidence=event_result["event_confidence"],
            relevance_score=relevance_score,
            matched_assets=matched_assets,
        )

        # Pre-filtro: si el determinista dice que la severidad es muy baja, no gastar LLM
        if impact_deterministic["severity"] < config.ALERT_SEVERITY_THRESHOLD * 0.5:
            logger.debug("Noticia descartada por severidad determinista muy baja: %.3f",
                         impact_deterministic["severity"])
            return None

        # --- Paso 5: Análisis contextual LLM (sobreescribe impacto + explicación) ---
        llm_analysis = await self.contextual_analyzer.analyze(
            title=title,
            text=cleaned_text,
            source=source,
            sentiment=event_result["sentiment"],
            matched_assets=matched_assets,
            relevance_score=relevance_score,
            portfolio=portfolio,
        )

        # Combinar impacto determinista con LLM
        impact = ImpactEstimator.merge_with_llm(impact_deterministic, llm_analysis)

        # Si el LLM refinó el tipo de evento, usarlo
        event_type = event_result["event_type"]
        if llm_analysis and llm_analysis.get("event_type"):
            event_type = llm_analysis["event_type"]

        # Filtro de severidad final
        if impact["severity"] < config.ALERT_SEVERITY_THRESHOLD:
            logger.debug("Noticia descartada por baja severidad: %.3f", impact["severity"])
            return None

        # --- Paso 6: Deduplicación semántica ---
        if self.deduplicator:
            is_dup, dup_sim = await self.deduplicator.is_duplicate(cleaned_text, news_id)
        else:
            is_dup, dup_sim = False, 0.0

        # --- Paso 7: Generación de explicación ---
        llm_explanation = llm_analysis.get("explanation", "") if llm_analysis else ""

        explanation = AlertExplainer.generate(
            title=title,
            matched_assets=matched_assets,
            event_type=event_type,
            direction=impact["direction"],
            severity_label=impact["severity_label"],
            confidence=impact["confidence"],
            relevance_score=relevance_score,
            source=source,
            sentiment=event_result["sentiment"]["sentiment"],
            llm_explanation=llm_explanation,
        )

        alert = Alert(
            news_id=news_id,
            news_title=title,
            news_url=url,
            news_source=source,
            matched_assets=matched_assets,
            event_type=event_type,
            direction=impact["direction"],
            severity=impact["severity"],
            severity_label=impact["severity_label"],
            confidence=impact["confidence"],
            relevance_score=relevance_score,
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
        alert = await self.process_news(
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

            # Notificación asíncrona (email + webhook)
            try:
                await NotificationService.notify(doc)
            except Exception:
                logger.exception("Error enviando notificación para alerta")

        return alert
