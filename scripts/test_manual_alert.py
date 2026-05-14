"""
Test con noticia manual relevante para forzar una alerta y verificar el pipeline completo.
"""
import asyncio
import sys
sys.path.insert(0, ".")

async def test_manual_alert():
    from database.mongodb import MongoDB
    from modules.alerts.engine import AlertEngine
    from modules.portfolio.models import Portfolio
    from modules.notifications.service import NotificationService

    await MongoDB.connect()

    # Obtener cartera
    pdoc = await MongoDB.portfolios().find_one({})
    pid = str(pdoc.pop("_id"))
    portfolio = Portfolio(**pdoc)
    print(f"Cartera: {portfolio.name} -> {portfolio.get_tickers()}")

    # Noticia ficticia RELEVANTE para NVDA
    title = "NVIDIA reports record Q1 2026 earnings, data center revenue surges 150%"
    summary = ("NVIDIA Corporation announced record-breaking first quarter results "
               "with data center revenue reaching $45 billion, driven by unprecedented "
               "demand for AI chips including Blackwell architecture GPUs. CEO Jensen Huang "
               "raised full-year guidance significantly above analyst expectations.")
    content = summary
    url = "https://example.com/nvidia-q1-2026"
    source = "test_manual"

    print(f"\nNoticia de prueba: {title}")
    print("Procesando...")

    engine = AlertEngine()
    alert = await engine.process_news(
        title=title,
        summary=summary,
        content=content,
        url=url,
        source=source,
        portfolio=portfolio,
        news_id="test_manual_001",
    )

    if alert:
        print(f"\n✅ ALERTA GENERADA:")
        print(f"  Título: {alert.news_title}")
        print(f"  Severidad: {alert.severity_label} ({alert.severity:.2f})")
        print(f"  Dirección: {alert.direction}")
        print(f"  Evento: {alert.event_type}")
        print(f"  Activos: {alert.matched_assets}")
        print(f"  Sentimiento: {alert.sentiment} ({alert.sentiment_confidence:.2f})")
        print(f"  Confianza: {alert.confidence:.2f}")
        print(f"  Duplicado: {alert.is_duplicate}")
        print(f"  Explicación: {alert.explanation[:200]}")

        # Intentar enviar notificación
        print(f"\n--- Enviando notificación ---")
        doc = alert.model_dump()
        doc["portfolio_id"] = pid
        result = await NotificationService.notify(doc)
        print(f"  Resultado: {result}")
        if result.get("email"):
            print("  ✅ Email enviado correctamente")
        else:
            print("  ⚠️  Email no enviado (revisa App Password en .env)")
    else:
        print("\n❌ No se generó alerta (filtrada por pipeline)")
        print("   Posibles causas: severidad baja, no relevante, o deduplicación")

    await MongoDB.close()

if __name__ == "__main__":
    asyncio.run(test_manual_alert())
