import asyncio
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    client = AsyncIOMotorClient("mongodb+srv://ruben:ruben@clusteinvesailert.gniynvm.mongodb.net/")
    db = client["portfolio_alerts"]

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
