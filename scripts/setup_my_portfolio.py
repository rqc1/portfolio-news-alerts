"""
Script para crear/actualizar la cartera personal en InvestAIlert.
Añade los activos y verifica persistencia en MongoDB Atlas.
"""
import asyncio
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URI = "mongodb+srv://ruben:ruben@clusteinvesailert.gniynvm.mongodb.net/"
DB_NAME = "portfolio_alerts"
USER_ID = "ruben"

ASSETS = [
    {"ticker": "MSFT", "name": "Microsoft Corporation", "sector": "Technology", "industry": "Software", "country": "US", "weight": 0.11, "aliases": ["Microsoft"]},
    {"ticker": "V", "name": "Visa Inc.", "sector": "Financial Services", "industry": "Credit Services", "country": "US", "weight": 0.11, "aliases": ["Visa"]},
    {"ticker": "TLN.MC", "name": "Talgo S.A.", "sector": "Industrials", "industry": "Railroads", "country": "ES", "weight": 0.11, "aliases": ["Talgo"]},
    {"ticker": "KAP.L", "name": "Kapital VCT plc", "sector": "Financial Services", "industry": "Asset Management", "country": "GB", "weight": 0.11, "aliases": ["Kapital"]},
    {"ticker": "NVDA", "name": "NVIDIA Corporation", "sector": "Technology", "industry": "Semiconductors", "country": "US", "weight": 0.12, "aliases": ["NVIDIA", "Nvidia"]},
    {"ticker": "TSM", "name": "Taiwan Semiconductor Manufacturing", "sector": "Technology", "industry": "Semiconductors", "country": "TW", "weight": 0.11, "aliases": ["TSMC", "Taiwan Semi"]},
    {"ticker": "NU", "name": "Nu Holdings Ltd.", "sector": "Financial Services", "industry": "Credit Services", "country": "BR", "weight": 0.11, "aliases": ["Nubank", "Nu"]},
    {"ticker": "AMD", "name": "Advanced Micro Devices Inc.", "sector": "Technology", "industry": "Semiconductors", "country": "US", "weight": 0.11, "aliases": ["AMD"]},
    {"ticker": "AVGO", "name": "Broadcom Inc.", "sector": "Technology", "industry": "Semiconductors", "country": "US", "weight": 0.11, "aliases": ["Broadcom"]},
]


async def main():
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]

    # Buscar cartera existente del usuario
    existing = await db.portfolios.find_one({"user_id": USER_ID})

    if existing:
        print(f"Cartera existente encontrada: {existing.get('name')} (id: {existing['_id']})")
        print(f"  Assets actuales: {len(existing.get('assets', []))}")

        # Actualizar assets
        result = await db.portfolios.update_one(
            {"_id": existing["_id"]},
            {
                "$set": {
                    "assets": ASSETS,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )
        print(f"  Actualizada: modified_count={result.modified_count}")
        portfolio_id = str(existing["_id"])
    else:
        print("No se encontró cartera. Creando nueva...")
        doc = {
            "user_id": USER_ID,
            "name": "Mi Cartera",
            "assets": ASSETS,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        result = await db.portfolios.insert_one(doc)
        portfolio_id = str(result.inserted_id)
        print(f"  Creada con id: {portfolio_id}")

    # Verificar persistencia
    print("\n--- Verificación de persistencia ---")
    saved = await db.portfolios.find_one({"user_id": USER_ID})
    print(f"Portfolio ID: {saved['_id']}")
    print(f"Nombre: {saved['name']}")
    print(f"Assets ({len(saved['assets'])}):")
    for a in saved["assets"]:
        print(f"  {a['ticker']:8s} | {a['name']:40s} | {a['sector']:20s} | {a['country']}")

    # Verificar colecciones
    print("\n--- Estado de colecciones ---")
    news_count = await db.news.count_documents({})
    alerts_count = await db.alerts.count_documents({})
    print(f"Noticias almacenadas: {news_count}")
    print(f"Alertas generadas: {alerts_count}")

    client.close()
    print("\n✅ Cartera persistida correctamente en MongoDB Atlas")


if __name__ == "__main__":
    asyncio.run(main())
