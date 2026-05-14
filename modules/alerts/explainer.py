"""
Generación de explicaciones para las alertas.

Dos modos:
  - LLM contextual: explicación personalizada generada por el LLM (preferida).
  - Template (fallback): texto generado con plantilla cuando el LLM no está disponible.
"""


class AlertExplainer:
    """Genera explicaciones legibles para alertas financieras."""

    DIRECTION_ES = {
        "alcista": "alcista",
        "bajista": "bajista",
        "neutral": "neutral",
    }

    EVENT_TYPE_ES = {
        "resultados_empresariales": "Resultados empresariales",
        "guidance_profit_warning": "Revisión de guidance / profit warning",
        "regulacion": "Acción regulatoria",
        "litigio": "Litigio / procedimiento legal",
        "fusion_adquisicion": "Fusión o adquisición",
        "ciberincidente": "Ciberincidente",
        "incidencia_operativa": "Incidencia operativa",
        "macroeconomia": "Evento macroeconómico",
        "cadena_suministro": "Cadena de suministro",
        "cambio_directivo": "Cambio directivo",
        "dividendo_recompra": "Dividendo / recompra de acciones",
        "otro": "Otro evento",
    }

    @staticmethod
    def generate(
        title: str,
        matched_assets: list[str],
        event_type: str,
        direction: str,
        severity_label: str,
        confidence: float,
        relevance_score: float,
        source: str,
        sentiment: str,
        llm_explanation: str = "",
    ) -> str:
        """
        Genera la explicación de la alerta.

        Si llm_explanation está disponible, la usa como base y añade metadatos.
        Si no, genera con template.
        """
        if llm_explanation:
            return AlertExplainer._enhance_llm_explanation(
                llm_explanation=llm_explanation,
                confidence=confidence,
                source=source,
            )

        return AlertExplainer._template_explanation(
            title=title,
            matched_assets=matched_assets,
            event_type=event_type,
            direction=direction,
            severity_label=severity_label,
            confidence=confidence,
            relevance_score=relevance_score,
            source=source,
            sentiment=sentiment,
        )

    @staticmethod
    def _enhance_llm_explanation(
        llm_explanation: str,
        confidence: float,
        source: str,
    ) -> str:
        """Usa la explicación del LLM y añade metadatos de trazabilidad."""
        parts = [llm_explanation.rstrip(".")]
        parts.append(f"Confianza: {confidence:.2f}. Fuente: {source}.")
        return ". ".join(parts)

    @staticmethod
    def _template_explanation(
        title: str,
        matched_assets: list[str],
        event_type: str,
        direction: str,
        severity_label: str,
        confidence: float,
        relevance_score: float,
        source: str,
        sentiment: str,
    ) -> str:
        """Fallback: explicación con template (sin LLM)."""
        event_desc = AlertExplainer.EVENT_TYPE_ES.get(event_type, event_type)
        assets_str = ", ".join(matched_assets) if matched_assets else "cartera general"

        parts = [
            f"Posible alerta {direction} de severidad {severity_label} para {assets_str}.",
            f"Evento detectado: {event_desc}.",
        ]

        # Razones de relevancia
        reasons = []
        if relevance_score >= 0.8:
            reasons.append("mención directa de activo en cartera")
        elif relevance_score >= 0.5:
            reasons.append("alta similitud semántica con la cartera")
        else:
            reasons.append("relevancia indirecta por sector o geografía")

        if sentiment != "neutral":
            reasons.append(f"sentimiento {sentiment} detectado por FinBERT")

        parts.append(f"Relevancia: {'; '.join(reasons)}.")
        parts.append(f"Confianza: {confidence:.2f}.")
        parts.append(f"Fuente: {source}.")

        return " ".join(parts)
