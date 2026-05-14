"""
Módulo 6 – Estimación de impacto.

Estima la dirección (alcista/bajista/neutral), severidad y confianza
del impacto de un evento detectado sobre los activos en cartera.

Dos modos:
  - Determinista (fallback): priors fijos por tipo de evento + heurísticas.
  - Contextual (LLM): el análisis LLM sobreescribe con valores contextualizados.
"""

import logging

logger = logging.getLogger(__name__)


# Matriz de severidad base por tipo de evento
# Cada tipo tiene una severidad media esperada y un sesgo de dirección típico
EVENT_IMPACT_PRIORS = {
    "resultados_empresariales": {"base_severity": 0.6, "direction_bias": 0.0},
    "guidance_profit_warning":  {"base_severity": 0.75, "direction_bias": -0.3},
    "regulacion":               {"base_severity": 0.65, "direction_bias": -0.2},
    "litigio":                  {"base_severity": 0.7, "direction_bias": -0.4},
    "fusion_adquisicion":       {"base_severity": 0.7, "direction_bias": 0.1},
    "ciberincidente":           {"base_severity": 0.8, "direction_bias": -0.5},
    "incidencia_operativa":     {"base_severity": 0.6, "direction_bias": -0.3},
    "macroeconomia":            {"base_severity": 0.5, "direction_bias": 0.0},
    "cadena_suministro":        {"base_severity": 0.6, "direction_bias": -0.2},
    "cambio_directivo":         {"base_severity": 0.5, "direction_bias": 0.0},
    "dividendo_recompra":       {"base_severity": 0.4, "direction_bias": 0.3},
    "otro":                     {"base_severity": 0.3, "direction_bias": 0.0},
}


class ImpactEstimator:
    """
    Estima dirección, severidad y confianza del impacto de una noticia.

    Combina:
    - Sentiment de FinBERT (polaridad)
    - Tipo de evento (priors de severidad)
    - Relevancia por cartera (amplificador)
    - Confianza del clasificador de eventos
    """

    @staticmethod
    def estimate(
        sentiment: dict,
        event_type: str,
        event_confidence: float,
        relevance_score: float,
        matched_assets: list[str],
    ) -> dict:
        # --- Dirección ---
        sent_label = sentiment.get("sentiment", "neutral")
        sent_conf = sentiment.get("confidence", 0.5)

        priors = EVENT_IMPACT_PRIORS.get(event_type, EVENT_IMPACT_PRIORS["otro"])

        # Dirección basada en sentimiento + sesgo del tipo de evento
        if sent_label == "positive":
            direction_score = 0.5 + sent_conf * 0.3 + priors["direction_bias"] * 0.2
        elif sent_label == "negative":
            direction_score = -0.5 - sent_conf * 0.3 + priors["direction_bias"] * 0.2
        else:
            direction_score = priors["direction_bias"] * 0.5

        if direction_score > 0.15:
            direction = "alcista"
        elif direction_score < -0.15:
            direction = "bajista"
        else:
            direction = "neutral"

        # --- Severidad ---
        base_severity = priors["base_severity"]

        # Amplificar si la relevancia es alta (mención directa)
        relevance_factor = 0.7 + 0.3 * relevance_score
        severity = base_severity * relevance_factor

        # Amplificar si el sentimiento es muy fuerte
        if sent_conf > 0.8:
            severity *= 1.1

        # El número de activos afectados aumenta la severidad percibida
        if len(matched_assets) > 1:
            severity *= 1.0 + 0.05 * min(len(matched_assets), 5)

        severity = min(severity, 1.0)

        # --- Confianza ---
        # Media ponderada de confianzas disponibles
        confidence = (
            0.3 * sent_conf
            + 0.4 * event_confidence
            + 0.3 * relevance_score
        )
        confidence = min(confidence, 1.0)

        return {
            "direction": direction,
            "direction_score": round(direction_score, 4),
            "severity": round(severity, 4),
            "severity_label": _severity_label(severity),
            "confidence": round(confidence, 4),
            "matched_assets": matched_assets,
        }

    @staticmethod
    def merge_with_llm(
        deterministic: dict,
        llm_analysis: dict | None,
    ) -> dict:
        """
        Combina la estimación determinista con el análisis contextual del LLM.

        Si el LLM proporcionó resultados, estos predominan para dirección,
        severidad y confianza (son contextualizados a la cartera).
        Si no hay LLM, devuelve la estimación determinista sin cambios.
        """
        if llm_analysis is None:
            return deterministic

        # El LLM prevalece en dirección, severidad y confianza
        severity = llm_analysis.get("severity", deterministic["severity"])
        confidence = llm_analysis.get("confidence", deterministic["confidence"])
        direction = llm_analysis.get("direction", deterministic["direction"])

        return {
            "direction": direction,
            "direction_score": deterministic["direction_score"],  # mantener el determinista como referencia
            "severity": round(severity, 4),
            "severity_label": _severity_label(severity),
            "confidence": round(confidence, 4),
            "matched_assets": deterministic["matched_assets"],
            "llm_enhanced": True,
        }


def _severity_label(severity: float) -> str:
    if severity >= 0.8:
        return "muy_alta"
    elif severity >= 0.6:
        return "alta"
    elif severity >= 0.4:
        return "media"
    elif severity >= 0.2:
        return "baja"
    return "muy_baja"
