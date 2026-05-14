"""
Test end-to-end: ingesta + procesamiento de alertas contra la cartera.
Simula lo que hace el scheduler automáticamente.
"""
import asyncio
import sys
sys.path.insert(0, ".")

async def test_e2e():
    from database.mongodb import MongoDB
    from modules.ingestion.service import IngestionService
    from modules.alerts.engine import AlertEngine
    from modules.portfolio.models import Portfolio
    from modules.notifications.service import NotificationService
    import config

    await MongoDB.connect()

    # 1. Obtener la cartera
    cursor = MongoDB.portfolios().find({})
    portfolios = await cursor.to_list(length=10)
    if not portfolios:
        print("ERROR: No hay carteras en la BD")
        return

    pdoc = portfolios[0]
    pid = str(pdoc.pop("_id"))
    portfolio = Portfolio(**pdoc)
    print(f"Cartera: {portfolio.name} ({len(portfolio.assets)} activos)")
    print(f"  Tickers: {portfolio.get_tickers()}")

    # 2. Obtener noticias recientes
    news_items = await IngestionService.get_recent_news(limit=30)
    print(f"\nNoticias recientes para procesar: {len(news_items)}")

    # 3. Procesar con AlertEngine
    print("\n=== Procesando alertas ===")
    engine = AlertEngine()
    alerts_generated = 0

    for i, item in enumerate(news_items[:30]):
        try:
            alert = await engine.process_news(
                title=item.get("title", ""),
                summary=item.get("summary", ""),
                content=item.get("content", ""),
                url=item.get("url", ""),
                source=item.get("source", ""),
                portfolio=portfolio,
                news_id=str(item.get("_id", "")),
            )
            if alert and not alert.is_duplicate:
                alerts_generated += 1
                print(f"\n  ALERTA #{alerts_generated}:")
                print(f"    Título: {alert.news_title[:80]}")
                print(f"    Severidad: {alert.severity_label} ({alert.severity:.2f})")
                print(f"    Dirección: {alert.direction}")
                print(f"    Evento: {alert.event_type}")
                print(f"    Activos: {alert.matched_assets}")
                print(f"    Explicación: {alert.explanation[:120]}...")
        except Exception as e:
            print(f"  Error en noticia {i}: {e}")

    print(f"\n=== Resultado ===")
    print(f"Noticias procesadas: {min(30, len(news_items))}")
    print(f"Alertas generadas: {alerts_generated}")

    # 4. Verificar estado de notificaciones
    print(f"\n=== Estado notificaciones ===")
    status = NotificationService.get_status()
    print(f"  Habilitadas: {status['enabled']}")
    print(f"  Email configurado: {status['email_configured']}")
    print(f"  Email destino: {status.get('email_to', 'N/A')}")
    print(f"  Webhook configurado: {status['webhook_configured']}")

    if not status['email_configured']:
        print("\n  ⚠️  SMTP no configurado - pon la App Password en .env para recibir emails")
    else:
        print("\n  ✅ Email listo para enviar alertas")

    # 5. Total alertas en BD
    total_alerts = await MongoDB.alerts().count_documents({})
    print(f"\nTotal alertas en BD: {total_alerts}")

    await MongoDB.close()
    print("\n✅ Test end-to-end completado")

if __name__ == "__main__":
    asyncio.run(test_e2e())
