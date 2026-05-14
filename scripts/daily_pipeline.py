"""
Pipeline diario de validación: ingesta → procesamiento → alertas.

Ejecutar: python -m scripts.daily_pipeline
Cada ejecución:
  1. Ingesta noticias de RSS (gratuito, sin API key)
  2. Procesa cada noticia contra la cartera (NLP + NLI + LLM)
  3. Muestra las alertas generadas con análisis completo
  4. Persiste todo en MongoDB para revisión posterior
"""

import asyncio
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from database.mongodb import MongoDB
from modules.portfolio.models import Portfolio
from modules.portfolio.service import PortfolioService
from modules.ingestion.service import IngestionService
from modules.alerts.engine import AlertEngine
from modules.market.service import MarketService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("daily_pipeline")

# ID de la cartera de validación (creada por setup_portfolio.py)
PORTFOLIO_ID = "69f2027828b140aeb16398e3"
USER_ID = "rquerol"


async def load_models():
    """Precarga modelos ML en memoria."""
    from modules.nlp.preprocessing import _load_spacy
    from modules.events.classifier import _load_finbert, _load_nli_pipeline
    from modules.relevance.service import _load_embedding_model
    logger.info("Cargando modelos ML...")
    _load_spacy()
    _load_finbert()
    _load_nli_pipeline()
    _load_embedding_model()
    logger.info("Modelos cargados ✓")


async def run_pipeline():
    await MongoDB.connect()
    logger.info("═" * 70)
    logger.info("PIPELINE DIARIO — %s", datetime.now().strftime("%Y-%m-%d %H:%M"))
    logger.info("═" * 70)

    # 1. Cargar cartera
    portfolio_doc = await PortfolioService.get_portfolio(PORTFOLIO_ID)
    if not portfolio_doc:
        logger.error("Cartera %s no encontrada. Ejecuta primero setup_portfolio.py", PORTFOLIO_ID)
        await MongoDB.close()
        return
    portfolio_doc.pop("_id", None)
    portfolio = Portfolio(**portfolio_doc)
    logger.info("Cartera: %s — Activos: %s", portfolio.name,
                [a.ticker for a in portfolio.assets])

    # 2. Precargar modelos
    await load_models()

    # 3. Ingesta RSS (gratuita)
    logger.info("─" * 70)
    logger.info("FASE 1: INGESTA DE NOTICIAS")
    logger.info("─" * 70)
    stats = await IngestionService.ingest_all(
        query="Visa OR Nvidia OR gold",
        tickers=["V", "NVDA", "GLD"],
    )
    logger.info("Ingesta completada: %s", stats)

    # 4. Procesar noticias recientes contra la cartera
    logger.info("─" * 70)
    logger.info("FASE 2: PROCESAMIENTO NLP + LLM")
    logger.info("─" * 70)
    engine = AlertEngine()
    news_items = await IngestionService.get_recent_news(limit=100)
    logger.info("Noticias a procesar: %d", len(news_items))

    alerts_generated = []
    discarded = 0
    duplicates = 0
    errors = 0

    for i, item in enumerate(news_items, 1):
        title = item.get("title", "")
        if not title:
            continue
        try:
            alert = await engine.process_and_store(
                title=title,
                summary=item.get("summary", ""),
                content=item.get("content", ""),
                url=item.get("url", ""),
                source=item.get("source", ""),
                portfolio=portfolio,
                portfolio_id=PORTFOLIO_ID,
                news_id=str(item.get("_id", "")),
            )
            if alert is None:
                discarded += 1
            elif alert.is_duplicate:
                duplicates += 1
            else:
                alerts_generated.append(alert)
                logger.info(
                    "  [%d/%d] ALERTA: %s → %s | sev=%s (%.1f) | dir=%s",
                    i, len(news_items),
                    title[:60],
                    alert.matched_assets,
                    alert.severity_label,
                    alert.severity,
                    alert.direction,
                )
        except Exception as e:
            errors += 1
            logger.warning("  [%d] Error procesando '%s': %s", i, title[:40], e)

    # 5. Resumen
    logger.info("═" * 70)
    logger.info("RESUMEN DEL DÍA")
    logger.info("═" * 70)
    logger.info("  Noticias procesadas: %d", len(news_items))
    logger.info("  Alertas generadas:   %d", len(alerts_generated))
    logger.info("  Duplicados:          %d", duplicates)
    logger.info("  Descartadas:         %d", discarded)
    logger.info("  Errores:             %d", errors)

    if alerts_generated:
        # Obtener fundamentales de los activos afectados (una vez por ticker)
        affected_tickers = set()
        for alert in alerts_generated:
            affected_tickers.update(alert.matched_assets)
        logger.info("Obteniendo datos fundamentales de: %s", list(affected_tickers))
        fundamentals_cache: dict[str, dict] = {}
        for ticker in affected_tickers:
            try:
                fund = MarketService.get_fundamentals(ticker)
                if fund:
                    fundamentals_cache[ticker] = fund
            except Exception as e:
                logger.warning("No se pudieron obtener fundamentales de %s: %s", ticker, e)

        logger.info("")
        logger.info("─" * 70)
        logger.info("ALERTAS DETALLADAS")
        logger.info("─" * 70)
        for j, alert in enumerate(alerts_generated, 1):
            logger.info("")
            logger.info("  📰 Alerta #%d", j)
            logger.info("     Título:     %s", alert.news_title[:100])
            logger.info("     Activos:    %s", alert.matched_assets)
            logger.info("     Evento:     %s", alert.event_type)
            logger.info("     Dirección:  %s", alert.direction)
            logger.info("     Severidad:  %s (%.2f/5)", alert.severity_label, alert.severity)
            logger.info("     Confianza:  %.0f%%", alert.confidence * 100)
            logger.info("     Relevancia: %.2f", alert.relevance_score)
            logger.info("     Sentimiento:%s (%.0f%%)", alert.sentiment,
                        alert.sentiment_confidence * 100)
            logger.info("     Fuente:     %s", alert.news_source)
            logger.info("     ─ Explicación ─")
            for line in alert.explanation.split(". "):
                if line.strip():
                    logger.info("     %s.", line.strip())

            # Fundamentales de cada activo afectado
            for ticker in alert.matched_assets:
                fund = fundamentals_cache.get(ticker)
                if fund:
                    logger.info("     ─ Fundamentales %s ─", ticker)
                    logger.info("     Precio: %.2f %s (%+.2f%%)",
                                fund["price"], fund["currency"], fund["change_pct"])
                    if fund.get("market_cap"):
                        cap_b = fund["market_cap"] / 1e9
                        logger.info("     Market Cap: %.1fB %s", cap_b, fund["currency"])
                    if fund.get("pe_trailing"):
                        logger.info("     P/E (TTM): %.1f | P/E (Fwd): %s",
                                    fund["pe_trailing"],
                                    f'{fund["pe_forward"]:.1f}' if fund.get("pe_forward") else "N/A")
                    if fund.get("eps_trailing"):
                        logger.info("     EPS (TTM): %.2f | EPS (Fwd): %s",
                                    fund["eps_trailing"],
                                    f'{fund["eps_forward"]:.2f}' if fund.get("eps_forward") else "N/A")
                    if fund.get("profit_margin") is not None:
                        logger.info("     Margen: %.1f%%", fund["profit_margin"] * 100)
                    if fund.get("dividend_yield") is not None:
                        logger.info("     Dividendo: %.2f%%", fund["dividend_yield"] * 100)
                    if fund.get("beta"):
                        logger.info("     Beta: %.2f", fund["beta"])
                    if fund.get("52w_high") and fund.get("52w_low"):
                        pct_from_high = ((fund["price"] - fund["52w_high"]) / fund["52w_high"]) * 100
                        logger.info("     52w: %.2f – %.2f (%.1f%% desde máx)",
                                    fund["52w_low"], fund["52w_high"], pct_from_high)
                    if fund.get("target_price"):
                        upside = ((fund["target_price"] - fund["price"]) / fund["price"]) * 100
                        logger.info("     Precio objetivo: %.2f (%+.1f%%) | Recom: %s",
                                    fund["target_price"], upside,
                                    fund.get("recommendation", "N/A"))
    else:
        logger.info("")
        logger.info("  ⚠️  No se generaron alertas hoy. Posibles razones:")
        logger.info("      - Las noticias no son relevantes para V, NVDA, GLD")
        logger.info("      - No superaron los umbrales de severidad/relevancia")

    logger.info("")
    logger.info("═" * 70)
    logger.info("Pipeline finalizado. Resultados guardados en MongoDB Atlas.")
    logger.info("═" * 70)

    await MongoDB.close()


if __name__ == "__main__":
    asyncio.run(run_pipeline())
