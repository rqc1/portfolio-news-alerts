import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("MONGO_DB_NAME", "portfolio_alerts")

async def main():
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]

    portfolios = await db.portfolios.find({}).to_list(100)
    print(f"Total carteras: {len(portfolios)}")
    for p in portfolios:
        assets = p.get("assets", [])
        tickers = [a["ticker"] for a in assets]
        pid = str(p["_id"])
        name = p.get("name", "?")
        user = p.get("user_id", "?")
        print(f"  ID: {pid}")
        print(f"  Nombre: {name}")
        print(f"  User: {user}")
        print(f"  Assets ({len(assets)}): {tickers}")
        print()

    client.close()

asyncio.run(main())
