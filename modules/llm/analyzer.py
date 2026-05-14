"""
Análisis contextual unificado con LLM.

Una única llamada LLM que reemplaza los módulos deterministas de estimación
de impacto y generación de explicación para noticias que pasan los filtros
baratos (relevancia + severidad mínima).

Produce: event_type + dirección + severidad + confianza + explicación,
todo contextualizado a la cartera específica del usuario.
"""

import json
import logging
from typing import Optional

from modules.llm.providers import get_llm_client
from modules.llm.prompts import (
    CONTEXTUAL_ANALYSIS_SYSTEM,
    CONTEXTUAL_ANALYSIS_USER,
    RELEVANCE_CHECK_SYSTEM,
    RELEVANCE_CHECK_USER,
)
from modules.portfolio.models import Portfolio

import config

logger = logging.getLogger(__name__)

# Valores válidos para validación de respuestas
_VALID_EVENTS = set(config.EVENT_TAXONOMY)
_VALID_DIRECTIONS = {"alcista", "bajista", "neutral"}


def _format_portfolio(portfolio: Portfolio) -> str:
    """Formatea la cartera como texto legible para el prompt del LLM."""
    lines = []
    for asset in portfolio.assets:
        parts = [f"{asset.ticker} — {asset.name}"]
        if asset.sector:
            parts.append(f"Sector: {asset.sector}")
        if asset.industry:
            parts.append(f"Industria: {asset.industry}")
        if asset.country:
            parts.append(f"País: {asset.country}")
        if asset.weight > 0:
            parts.append(f"Peso: {asset.weight:.1%}")
        lines.append(" | ".join(parts))
    return "\n".join(lines) if lines else "Cartera vacía"


def _safe_parse_json(text: str) -> Optional[dict]:
    """Parsea JSON de la respuesta LLM, tolerando bloques markdown."""
    text = text.strip()
    # Eliminar bloques ```json ... ```
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [line for line in lines if not line.strip().startswith("```")]
        text = "\n".join(lines).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Buscar JSON embebido en la respuesta
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass
    return None


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


class ContextualAnalyzer:
    """
    Análisis contextual de impacto mediante LLM.

    Una sola llamada que produce: tipo de evento, dirección, severidad,
    confianza y explicación — todo contextualizado a la cartera del usuario.
    """

    async def analyze(
        self,
        title: str,
        text: str,
        source: str,
        sentiment: dict,
        matched_assets: list[str],
        relevance_score: float,
        portfolio: Portfolio,
    ) -> Optional[dict]:
        """
        Análisis contextual unificado.

        Returns dict con: event_type, direction, severity, confidence,
        explanation, reasoning, source="llm".
        Returns None si el LLM no está disponible (fallback a determinista).
        """
        client = get_llm_client()
        if not client.is_available():
            logger.info("LLM no disponible, se usará análisis determinista")
            return None

        portfolio_desc = _format_portfolio(portfolio)
        assets_str = (
            ", ".join(matched_assets)
            if matched_assets
            else "Ninguno (relevancia indirecta por sector/geografía)"
        )

        user_prompt = CONTEXTUAL_ANALYSIS_USER.format(
            title=title,
            source=source,
            text=text[:1500],  # Truncar para no exceder context window
            sentiment=sentiment.get("sentiment", "neutral"),
            sentiment_confidence=sentiment.get("confidence", 0.5),
            portfolio_description=portfolio_desc,
            matched_assets=assets_str,
            relevance_score=relevance_score,
        )

        try:
            raw = await client.chat(
                system_prompt=CONTEXTUAL_ANALYSIS_SYSTEM,
                user_prompt=user_prompt,
                temperature=0.15,
                max_tokens=600,
            )
            result = _safe_parse_json(raw)
            if result is None:
                logger.warning("No se pudo parsear la respuesta LLM como JSON: %s", raw[:200])
                return None

            # Validar y normalizar
            event_type = result.get("event_type", "otro")
            if event_type not in _VALID_EVENTS:
                event_type = "otro"

            direction = result.get("direction", "neutral")
            if direction not in _VALID_DIRECTIONS:
                direction = "neutral"

            severity = _clamp(float(result.get("severity", 0.5)))
            confidence = _clamp(float(result.get("confidence", 0.5)))

            return {
                "event_type": event_type,
                "direction": direction,
                "severity": round(severity, 4),
                "confidence": round(confidence, 4),
                "explanation": result.get("explanation", ""),
                "reasoning": result.get("reasoning", ""),
                "source": "llm",
            }

        except Exception:
            logger.exception("Análisis contextual LLM falló")
            return None


class RelevanceChecker:
    """
    Filtro de relevancia de segundo nivel con LLM.

    Para noticias en la zona borderline (entre threshold_low y threshold),
    el LLM evalúa si hay relevancia indirecta que los filtros automáticos no captan.
    """

    async def check(
        self,
        title: str,
        summary: str,
        portfolio: Portfolio,
    ) -> Optional[dict]:
        """
        Comprueba relevancia indirecta con LLM.

        Returns dict con: is_relevant, relevance_score, reason, affected_assets.
        Returns None si el LLM no está disponible.
        """
        client = get_llm_client()
        if not client.is_available():
            return None

        portfolio_desc = _format_portfolio(portfolio)

        user_prompt = RELEVANCE_CHECK_USER.format(
            title=title,
            summary=summary[:500],
            portfolio_description=portfolio_desc,
        )

        try:
            raw = await client.chat(
                system_prompt=RELEVANCE_CHECK_SYSTEM,
                user_prompt=user_prompt,
                temperature=0.1,
                max_tokens=200,
            )
            result = _safe_parse_json(raw)
            if result is None:
                logger.warning("No se pudo parsear respuesta de relevancia LLM")
                return None

            return {
                "is_relevant": bool(result.get("is_relevant", False)),
                "relevance_score": _clamp(float(result.get("relevance_score", 0.0))),
                "reason": result.get("reason", ""),
                "affected_assets": result.get("affected_assets", []),
            }

        except Exception:
            logger.exception("Relevance check LLM falló")
            return None
