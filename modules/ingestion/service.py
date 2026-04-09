"""
Servicio orquestador de ingesta de noticias.

Coordina la adquisición desde todas las fuentes, deduplica por hash
y persiste en MongoDB.
"""

import logging

from pymongo.errors import DuplicateKeyError

import config
from database.mongodb import MongoDB
from modules.ingestion.models import NewsItem
from modules.ingestion.rss_feeds import fetch_all_rss
from modules.ingestion.cnmv import fetch_all_cnmv
from modules.ingestion.sec_edgar import search_recent_filings
from modules.ingestion.newsapi import search_newsapi
from modules.ingestion.alphavantage import fetch_alphavantage_news

logger = logging.getLogger(__name__)


class IngestionService:

    @staticmethod
    async def ingest_all(
        query: str = "",
        tickers: list[str] | None = None,
    ) -> dict:
        """Ejecuta la ingesta completa desde todas las fuentes."""
        stats = {
            "rss": 0, "cnmv": 0, "sec": 0,
            "newsapi": 0, "alphavantage": 0,
            "duplicates": 0, "errors": 0,
        }

        # RSS genéricos (incluye macro, cyber, supply chain, prensa española)
        rss_items = fetch_all_rss(config.RSS_FEEDS)
        stats["rss"] = await IngestionService._persist_items(rss_items, stats)

        # CNMV
        cnmv_items = fetch_all_cnmv()
        stats["cnmv"] = await IngestionService._persist_items(cnmv_items, stats)

        # SEC EDGAR
        sec_items = await search_recent_filings(
            query=query, form_types=["8-K", "10-K", "10-Q"], limit=30
        )
        stats["sec"] = await IngestionService._persist_items(sec_items, stats)

        # NewsAPI (texto completo, cobertura global)
        if config.NEWSAPI_KEY and query:
            newsapi_items = await search_newsapi(query, page_size=30)
            stats["newsapi"] = await IngestionService._persist_items(newsapi_items, stats)

        # Alpha Vantage (tickers anotados + sentimiento)
        if config.ALPHAVANTAGE_KEY and tickers:
            av_items = await fetch_alphavantage_news(tickers=tickers, limit=30)
            stats["alphavantage"] = await IngestionService._persist_items(av_items, stats)

        logger.info("Ingestion complete: %s", stats)
        return stats

    @staticmethod
    async def ingest_rss_only() -> int:
        items = fetch_all_rss(config.RSS_FEEDS)
        stats = {"duplicates": 0, "errors": 0}
        count = await IngestionService._persist_items(items, stats)
        return count

    @staticmethod
    async def ingest_cnmv_only() -> int:
        items = fetch_all_cnmv()
        stats = {"duplicates": 0, "errors": 0}
        count = await IngestionService._persist_items(items, stats)
        return count

    @staticmethod
    async def ingest_newsapi(query: str, language: str = "en") -> int:
        items = await search_newsapi(query, language=language, page_size=30)
        stats = {"duplicates": 0, "errors": 0}
        return await IngestionService._persist_items(items, stats)

    @staticmethod
    async def ingest_alphavantage(tickers: list[str]) -> int:
        items = await fetch_alphavantage_news(tickers=tickers, limit=30)
        stats = {"duplicates": 0, "errors": 0}
        return await IngestionService._persist_items(items, stats)

    @staticmethod
    async def _persist_items(items: list[NewsItem], stats: dict) -> int:
        saved = 0
        for item in items:
            try:
                await MongoDB.news().insert_one(item.model_dump())
                saved += 1
            except DuplicateKeyError:
                stats["duplicates"] = stats.get("duplicates", 0) + 1
            except Exception:
                stats["errors"] = stats.get("errors", 0) + 1
                logger.exception("Error persisting news item: %s", item.url)
        return saved

    @staticmethod
    async def get_recent_news(limit: int = 50) -> list[dict]:
        cursor = MongoDB.news().find().sort("published_at", -1).limit(limit)
        return await cursor.to_list(length=limit)
