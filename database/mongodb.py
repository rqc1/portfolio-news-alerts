"""
Capa de acceso a datos – MongoDB.
"""

from datetime import datetime, timezone
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, DESCENDING, TEXT

import config


class MongoDB:
    _client: AsyncIOMotorClient | None = None
    _db: Any = None

    @classmethod
    async def connect(cls) -> None:
        kwargs = {}
        try:
            import certifi
            kwargs["tlsCAFile"] = certifi.where()
        except ImportError:
            pass
        cls._client = AsyncIOMotorClient(config.MONGO_URI, **kwargs)
        cls._db = cls._client[config.MONGO_DB_NAME]
        await cls._ensure_indexes()

    @classmethod
    async def close(cls) -> None:
        if cls._client:
            cls._client.close()

    @classmethod
    def get_db(cls):
        if cls._db is None:
            raise RuntimeError("Database not connected. Call MongoDB.connect() first.")
        return cls._db

    # --- Collections ---
    @classmethod
    def portfolios(cls):
        return cls.get_db()["portfolios"]

    @classmethod
    def news(cls):
        return cls.get_db()["news"]

    @classmethod
    def alerts(cls):
        return cls.get_db()["alerts"]

    @classmethod
    def events(cls):
        return cls.get_db()["events"]

    @classmethod
    def dedup_embeddings(cls):
        return cls.get_db()["dedup_embeddings"]

    # --- Indexes ---
    @classmethod
    async def _ensure_indexes(cls) -> None:
        # News
        await cls.news().create_index([("url", ASCENDING)], unique=True)
        await cls.news().create_index([("published_at", DESCENDING)])
        await cls.news().create_index([("source", ASCENDING)])
        await cls.news().create_index([("content_hash", ASCENDING)])
        await cls.news().create_index([("title", TEXT), ("summary", TEXT)])

        # Alerts
        await cls.alerts().create_index([("created_at", DESCENDING)])
        await cls.alerts().create_index([("portfolio_id", ASCENDING)])
        await cls.alerts().create_index([("severity", DESCENDING)])

        # Portfolios
        await cls.portfolios().create_index([("user_id", ASCENDING)])

        # Dedup embeddings (TTL: 30 días)
        await cls.dedup_embeddings().create_index(
            [("created_at", ASCENDING)],
            expireAfterSeconds=30 * 24 * 3600,
        )
        await cls.dedup_embeddings().create_index([("alert_id", ASCENDING)])

    # --- Generic helpers ---
    @classmethod
    async def insert_one(cls, collection_name: str, document: dict) -> str:
        document.setdefault("created_at", datetime.now(timezone.utc))
        result = await cls.get_db()[collection_name].insert_one(document)
        return str(result.inserted_id)

    @classmethod
    async def find(cls, collection_name: str, query: dict, limit: int = 100):
        cursor = cls.get_db()[collection_name].find(query).limit(limit)
        return await cursor.to_list(length=limit)
