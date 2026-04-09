"""
Generación de explicaciones para las alertas.
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
    ) -> str:
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
