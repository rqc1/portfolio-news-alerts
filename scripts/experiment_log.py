"""
Utilidad para registrar resultados experimentales en RESULTADOS_EXPERIMENTALES.md.

Cada ejecución de un experimento (pipeline diario, comparación multi-modelo, etc.)
añade una nueva sección fechada al final del documento. Las entradas se ANEXAN,
nunca se sobrescriben, manteniendo un histórico completo.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

# Documento de resultados en la raíz del proyecto
RESULTS_DOC = Path(__file__).resolve().parent.parent / "RESULTADOS_EXPERIMENTALES.md"


def append_experiment(title: str, body_md: str) -> Path:
    """Anexa una sección fechada al documento de resultados experimentales.

    Args:
        title: título corto del experimento (sin fecha; se antepone automáticamente).
        body_md: cuerpo en Markdown ya formateado (tablas, listas, etc.).

    Returns:
        Ruta del documento actualizado.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    date_only = datetime.now().strftime("%Y-%m-%d")

    section = f"\n---\n\n## {date_only} — {title}\n\n*Ejecución: {timestamp}*\n\n{body_md.rstrip()}\n"

    # Crear el documento con cabecera si no existe
    if not RESULTS_DOC.exists():
        header = (
            "# Resultados Experimentales — InvestAIlert\n\n"
            "Registro histórico fechado de todas las ejecuciones experimentales. "
            "**Las entradas se añaden, nunca se sobrescriben.**\n"
        )
        RESULTS_DOC.write_text(header, encoding="utf-8")

    with RESULTS_DOC.open("a", encoding="utf-8") as f:
        f.write(section)

    return RESULTS_DOC
