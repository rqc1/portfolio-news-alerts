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


# Caché del calibrador empírico (score de severidad → |CAR| esperado → label).
# Se rellena de forma perezosa desde el fichero ajustado por backtesting y se
# invalida si el fichero cambia (mtime). Si no existe, el sistema funciona
# exactamente igual que antes (degradación elegante).
_CALIBRATOR_CACHE: dict = {"path": None, "mtime": None, "obj": None}


def _load_severity_calibrator():
    """Devuelve el `SeverityCalibrator` ajustado o None si no hay fichero.

    Cierra el bucle de feedback: el calibrador lo ajusta
    `AlertBacktestService.fit_calibrator` con datos reales (|CAR| observado),
    y aquí se carga para anclar la etiqueta de severidad a evidencia empírica.
    """
    try:
        import os
        import config

        path = getattr(config, "SEVERITY_CALIBRATOR_PATH", None)
        if not path or not os.path.exists(path):
            return None
        mtime = os.path.getmtime(path)
        if _CALIBRATOR_CACHE["path"] == path and _CALIBRATOR_CACHE["mtime"] == mtime:
            return _CALIBRATOR_CACHE["obj"]

        from modules.impact.calibration import SeverityCalibrator

        cal = SeverityCalibrator.load(path)
        _CALIBRATOR_CACHE.update({"path": path, "mtime": mtime, "obj": cal})
        return cal
    except Exception:  # noqa: BLE001 — nunca debe romper la estimación
        logger.debug("No se pudo cargar el calibrador de severidad", exc_info=True)
        return None


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

        result = {
            "direction": direction,
            "direction_score": round(direction_score, 4),
            "severity": round(severity, 4),
            "severity_label": _severity_label(severity),
            "confidence": round(confidence, 4),
            "matched_assets": matched_assets,
        }

        # --- Anclaje empírico (feedback loop) ---
        # Si existe un calibrador ajustado por backtesting, derivar una etiqueta
        # de severidad anclada al |CAR| esperado. No modifica el score continuo
        # (que sigue alimentando el calibrador), solo añade evidencia empírica.
        cal = _load_severity_calibrator()
        if cal is not None:
            from modules.impact.calibration import abs_car_to_label

            expected_abs_car = cal.expected_abs_car(severity)
            result["expected_abs_car"] = round(float(expected_abs_car), 6)
            result["severity_label_calibrated"] = abs_car_to_label(expected_abs_car)

        return result


    @staticmethod
    def merge_with_llm(
        deterministic: dict,
        llm_analysis: dict | None,
        max_severity_adjustment: float = 0.2,
        direction_confidence_threshold: float = 0.6,
    ) -> dict:
        """
        Combina la estimación determinista con el análisis contextual del LLM
        aplicando guardarraíles que evitan que el LLM degrade la calidad.

        Motivación empírica: en la ablación, sobrescribir ciegamente la
        severidad con el valor del LLM empeoraba el MAE de severidad
        (0.593 → 1.034). El LLM aporta contexto valioso, pero su severidad
        está mal calibrada. Por ello:

          - Severidad: el LLM solo puede AJUSTAR la severidad determinista
            dentro de una banda de ±``max_severity_adjustment`` (clamp). El
            estimador determinista, anclado a priors por tipo de evento y a
            la relevancia, actúa como ancla calibrada.
          - Dirección: se acepta la dirección del LLM solo si su confianza
            supera ``direction_confidence_threshold`` o si coincide con la
            determinista; de lo contrario prevalece la determinista.
          - Confianza: se combina (media) en lugar de sobrescribir, para no
            heredar el exceso de confianza del LLM.

        Si no hay análisis LLM, devuelve la estimación determinista sin cambios.
        """
        if llm_analysis is None:
            return deterministic

        det_severity = deterministic["severity"]
        det_direction = deterministic["direction"]
        det_confidence = deterministic["confidence"]

        # --- Severidad: ajuste acotado alrededor del ancla determinista ---
        llm_severity = llm_analysis.get("severity", det_severity)
        try:
            llm_severity = float(llm_severity)
        except (TypeError, ValueError):
            llm_severity = det_severity
        lo = max(0.0, det_severity - max_severity_adjustment)
        hi = min(1.0, det_severity + max_severity_adjustment)
        severity = min(max(llm_severity, lo), hi)

        # --- Dirección: aceptar LLM solo si es fiable o coincide ---
        llm_direction = llm_analysis.get("direction", det_direction)
        llm_conf = llm_analysis.get("confidence", det_confidence)
        try:
            llm_conf = float(llm_conf)
        except (TypeError, ValueError):
            llm_conf = det_confidence

        if llm_direction == det_direction:
            direction = det_direction
        elif llm_conf >= direction_confidence_threshold:
            direction = llm_direction
        else:
            direction = det_direction

        # --- Confianza: combinación, no sobrescritura ---
        confidence = min(0.5 * det_confidence + 0.5 * llm_conf, 1.0)

        return {
            "direction": direction,
            "direction_score": deterministic["direction_score"],
            "severity": round(severity, 4),
            "severity_label": _severity_label(severity),
            "confidence": round(confidence, 4),
            "matched_assets": deterministic["matched_assets"],
            "llm_enhanced": True,
            "llm_severity_raw": round(llm_severity, 4),
            "llm_direction_raw": llm_direction,
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
