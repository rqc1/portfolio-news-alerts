"""
Scheduler – Ingesta automática y procesamiento periódico de alertas.

Ejecuta en background:
  1. Ingesta RSS + CNMV cada N minutos (configurable).
  2. Procesamiento batch de alertas para todas las carteras.
  3. Limpieza de noticias antiguas.

Usa APScheduler (AsyncIOScheduler) integrado en el event loop de FastAPI.
"""

import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

import config
from database.mongodb import MongoDB
from modules.ingestion.service import IngestionService
from modules.portfolio.models import Portfolio

logger = logging.getLogger(__name__)

# Referencia global al scheduler para poder detenerlo desde lifespan
_scheduler: AsyncIOScheduler | None = None


async def _job_ingest_feeds():
    """Job periódico: ingesta de RSS + CNMV."""
    logger.info("[Scheduler] Iniciando ingesta automática de RSS + CNMV")
    try:
        rss_count = await IngestionService.ingest_rss_only()
        cnmv_count = await IngestionService.ingest_cnmv_only()
        logger.info(
            "[Scheduler] Ingesta completada — RSS: %d, CNMV: %d nuevas noticias",
            rss_count,
            cnmv_count,
        )
    except Exception:
        logger.exception("[Scheduler] Error en ingesta automática")


async def _job_process_alerts(alert_engine):
    """Job periódico: procesa noticias recientes contra todas las carteras."""
    logger.info("[Scheduler] Iniciando procesamiento batch de alertas")
    try:
        # Obtener todas las carteras
        cursor = MongoDB.portfolios().find({})
        portfolios = await cursor.to_list(length=200)

        if not portfolios:
            logger.debug("[Scheduler] No hay carteras, omitiendo procesamiento")
            return

        # Noticias recientes no procesadas (últimas N)
        news_items = await IngestionService.get_recent_news(
            limit=config.SCHEDULER_BATCH_SIZE
        )

        total_alerts = 0
        for pdoc in portfolios:
            pid = str(pdoc.pop("_id"))
            portfolio = Portfolio(**pdoc)

            for item in news_items:
                try:
                    alert = await alert_engine.process_and_store(
                        title=item.get("title", ""),
                        summary=item.get("summary", ""),
                        content=item.get("content", ""),
                        url=item.get("url", ""),
                        source=item.get("source", ""),
                        portfolio=portfolio,
                        portfolio_id=pid,
                        news_id=str(item.get("_id", "")),
                    )
                    if alert and not alert.is_duplicate:
                        total_alerts += 1
                except Exception:
                    logger.exception(
                        "[Scheduler] Error procesando noticia %s para cartera %s",
                        item.get("url", "?"),
                        pid,
                    )

        logger.info(
            "[Scheduler] Procesamiento completado — %d carteras × %d noticias → %d alertas nuevas",
            len(portfolios),
            len(news_items),
            total_alerts,
        )
    except Exception:
        logger.exception("[Scheduler] Error en procesamiento batch de alertas")


async def _job_cleanup_old_news():
    """Job periódico: elimina noticias más antiguas que SCHEDULER_NEWS_RETENTION_DAYS."""
    from datetime import timedelta

    cutoff = datetime.now(timezone.utc) - timedelta(
        days=config.SCHEDULER_NEWS_RETENTION_DAYS
    )
    try:
        result = await MongoDB.news().delete_many({"published_at": {"$lt": cutoff}})
        if result.deleted_count > 0:
            logger.info(
                "[Scheduler] Limpieza: %d noticias antiguas eliminadas (antes de %s)",
                result.deleted_count,
                cutoff.isoformat(),
            )
    except Exception:
        logger.exception("[Scheduler] Error en limpieza de noticias antiguas")


def start_scheduler(alert_engine) -> AsyncIOScheduler:
    """
    Arranca el scheduler con los jobs configurados.

    Llamar desde el lifespan de FastAPI (después de conectar a MongoDB).
    """
    global _scheduler

    if not config.SCHEDULER_ENABLED:
        logger.info("[Scheduler] Desactivado (SCHEDULER_ENABLED=false)")
        return None

    scheduler = AsyncIOScheduler(timezone="UTC")

    # Job 1: Ingesta de RSS + CNMV
    scheduler.add_job(
        _job_ingest_feeds,
        trigger=IntervalTrigger(minutes=config.SCHEDULER_INGEST_INTERVAL_MIN),
        id="ingest_feeds",
        name="Ingesta automática RSS + CNMV",
        replace_existing=True,
        max_instances=1,
    )

    # Job 2: Procesamiento de alertas
    scheduler.add_job(
        _job_process_alerts,
        args=[alert_engine],
        trigger=IntervalTrigger(minutes=config.SCHEDULER_ALERTS_INTERVAL_MIN),
        id="process_alerts",
        name="Procesamiento batch de alertas",
        replace_existing=True,
        max_instances=1,
    )

    # Job 3: Limpieza de noticias antiguas (1 vez al día)
    scheduler.add_job(
        _job_cleanup_old_news,
        trigger=IntervalTrigger(hours=24),
        id="cleanup_old_news",
        name="Limpieza de noticias antiguas",
        replace_existing=True,
        max_instances=1,
    )

    scheduler.start()
    _scheduler = scheduler
    logger.info(
        "[Scheduler] Iniciado — ingesta cada %d min, alertas cada %d min, limpieza diaria",
        config.SCHEDULER_INGEST_INTERVAL_MIN,
        config.SCHEDULER_ALERTS_INTERVAL_MIN,
    )
    return scheduler


def stop_scheduler():
    """Detiene el scheduler de forma limpia."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("[Scheduler] Detenido")
        _scheduler = None


def get_scheduler_status() -> dict:
    """Devuelve el estado actual del scheduler y sus jobs."""
    if _scheduler is None or not _scheduler.running:
        return {"enabled": False, "running": False, "jobs": []}

    jobs = []
    for job in _scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
        })

    return {"enabled": True, "running": True, "jobs": jobs}
