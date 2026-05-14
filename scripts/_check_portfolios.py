import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    client = AsyncIOMotorClient("mongodb+srv://ruben:ruben@clusteinvesailert.gniynvm.mongodb.net/")
    db = client["portfolio_alerts"]

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
