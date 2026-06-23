"""
Logging estructurado (structlog) para la capa de producción.

`configure_logging` deja el logging estándar y structlog alineados. En modo
JSON (recomendado en producción) cada línea es un objeto JSON con timestamp,
nivel, logger y contexto enlazado (request_id, ruta, latencia…), apto para
agregadores (Loki, ELK, Datadog). En desarrollo usa salida en consola legible.
"""

from __future__ import annotations

import logging
import sys

import structlog


def configure_logging(json_logs: bool = False, level: str = "INFO") -> None:
    log_level = getattr(logging, level.upper(), logging.INFO)

    timestamper = structlog.processors.TimeStamper(fmt="iso")
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        timestamper,
    ]

    if json_logs:
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=False)

    structlog.configure(
        processors=shared_processors + [
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )

    # Alinear el logging estándar (uvicorn, librerías) al mismo nivel.
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )


def get_logger(name: str = "investailert"):
    return structlog.get_logger(name)
