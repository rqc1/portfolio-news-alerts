"""
Ejecución completa: ingesta + procesamiento de alertas + guardado de resultados.
"""
import asyncio
import json
import sys
from datetime import datetime, timezone

sys.path.insert(0, ".")


async def run_full_pipeline():
    from database.mongodb import MongoDB
    from modules.ingestion.service import IngestionService
    from modules.alerts.engine import AlertEngine
    from modules.portfolio.models import Portfolio

    await MongoDB.connect()

    # 1. Ingesta
    print("=== INGESTA ===")
    rss_count = await IngestionService.ingest_rss_only()
    print(f"Nuevas noticias RSS: {rss_count}")
    total_news = await MongoDB.news().count_documents({})
    print(f"Total noticias en BD: {total_news}")

    # 2. Obtener cartera
    pdoc = await MongoDB.portfolios().find_one({})
    pid = str(pdoc.pop("_id"))
    portfolio = Portfolio(**pdoc)
    print(f"\nCartera: {portfolio.name} ({len(portfolio.assets)} activos)")
    print(f"Tickers: {portfolio.get_tickers()}")

    # 3. Procesar todas las noticias recientes (batch grande)
    print("\n=== PROCESAMIENTO DE ALERTAS ===")
    news_items = await IngestionService.get_recent_news(limit=100)
    print(f"Noticias a procesar: {len(news_items)}")

    engine = AlertEngine()
    alerts_generated = []

    for i, item in enumerate(news_items):
        try:
            alert = await engine.process_and_store(
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
                alerts_generated.append(alert.model_dump())
                print(f"\n  ALERTA #{len(alerts_generated)}: {alert.news_title[:70]}")
                print(f"    Severidad: {alert.severity_label} | Dirección: {alert.direction} | Activos: {alert.matched_assets}")
        except Exception as e:
            pass  # Skip individual errors silently

    # 4. Guardar resultados
    print(f"\n=== RESULTADOS ===")
    print(f"Noticias procesadas: {len(news_items)}")
    print(f"Alertas nuevas generadas: {len(alerts_generated)}")

    total_alerts = await MongoDB.alerts().count_documents({})
    print(f"Total alertas en BD: {total_alerts}")

    # Guardar resumen en archivo
    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "news_ingested": rss_count,
        "total_news_in_db": total_news + rss_count,
        "news_processed": len(news_items),
        "alerts_generated": len(alerts_generated),
        "total_alerts_in_db": total_alerts,
        "portfolio_tickers": portfolio.get_tickers(),
        "alerts": [
            {
                "title": a["news_title"][:100],
                "severity": a["severity_label"],
                "direction": a["direction"],
                "event_type": a["event_type"],
                "matched_assets": a["matched_assets"],
                "confidence": a["confidence"],
                "url": a["news_url"],
            }
            for a in alerts_generated
        ],
    }

    with open("scripts/last_run_results.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"\nResultados guardados en scripts/last_run_results.json")
    await MongoDB.close()
    print("✅ Pipeline completado")


if __name__ == "__main__":
    asyncio.run(run_full_pipeline())
