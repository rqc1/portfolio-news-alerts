"""
Servicio de gestión de carteras – CRUD y normalización.
"""

from bson import ObjectId
from datetime import datetime, timezone

from database.mongodb import MongoDB
from modules.portfolio.models import Portfolio, Asset


class PortfolioService:

    @staticmethod
    async def create_portfolio(portfolio: Portfolio) -> str:
        doc = portfolio.model_dump()
        result = await MongoDB.portfolios().insert_one(doc)
        return str(result.inserted_id)

    @staticmethod
    async def get_portfolio(portfolio_id: str) -> dict | None:
        doc = await MongoDB.portfolios().find_one({"_id": ObjectId(portfolio_id)})
        if doc is None:
            return None
        doc["_id"] = str(doc["_id"])
        return doc

    @staticmethod
    async def get_portfolios_by_user(user_id: str) -> list[dict]:
        cursor = MongoDB.portfolios().find({"user_id": user_id})
        docs = await cursor.to_list(length=50)
        for doc in docs:
            doc["_id"] = str(doc["_id"])
        return docs

    @staticmethod
    async def add_asset(portfolio_id: str, asset: Asset) -> bool:
        result = await MongoDB.portfolios().update_one(
            {"_id": ObjectId(portfolio_id)},
            {
                "$push": {"assets": asset.model_dump()},
                "$set": {"updated_at": datetime.now(timezone.utc)},
            },
        )
        return result.modified_count > 0

    @staticmethod
    async def remove_asset(portfolio_id: str, ticker: str) -> bool:
        result = await MongoDB.portfolios().update_one(
            {"_id": ObjectId(portfolio_id)},
            {
                "$pull": {"assets": {"ticker": ticker}},
                "$set": {"updated_at": datetime.now(timezone.utc)},
            },
        )
        return result.modified_count > 0

    @staticmethod
    async def delete_portfolio(portfolio_id: str) -> bool:
        result = await MongoDB.portfolios().delete_one({"_id": ObjectId(portfolio_id)})
        return result.deleted_count > 0
