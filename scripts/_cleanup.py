import asyncio
import os
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("MONGO_DB_NAME", "portfolio_alerts")

async def main():
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]

    # Borrar cartera vieja de validacion
    result = await db.portfolios.delete_one({"_id": ObjectId("69f2027828b140aeb16398e3")})
    print(f"Cartera vieja eliminada: {result.deleted_count}")

    # Verificar
    remaining = await db.portfolios.find({}).to_list(10)
    print(f"Carteras restantes: {len(remaining)}")
    for p in remaining:
        tickers = [a["ticker"] for a in p.get("assets", [])]
        print(f"  {p['name']} -> {tickers}")

    client.close()

asyncio.run(main())
