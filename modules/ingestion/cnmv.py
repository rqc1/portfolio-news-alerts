"""
Ingesta de noticias desde feeds RSS de la CNMV.
"""

import asyncio
import hashlib
import logging
from datetime import datetime, timezone

import feedparser

import config
from modules.ingestion.models import NewsItem

logger = logging.getLogger(__name__)


def _parse_date(entry) -> datetime:
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        from calendar import timegm
        return datetime.fromtimestamp(timegm(entry.published_parsed), tz=timezone.utc)
    return datetime.now(timezone.utc)


def _fetch_cnmv_feed_sync(feed_name: str, feed_url: str) -> list[NewsItem]:
    """Descarga un feed RSS de la CNMV (bloqueante)."""
    items: list[NewsItem] = []
    try:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries:
            title = getattr(entry, "title", "")
            summary = getattr(entry, "summary", "")
            link = getattr(entry, "link", "")
            if not link:
                continue

            full_text = f"{title} {summary}"
            item = NewsItem(
                title=title,
                summary=summary,
                url=link,
                source=f"cnmv_{feed_name}",
                source_type="cnmv",
                published_at=_parse_date(entry),
                language="es",
                content_hash=hashlib.sha256(full_text.encode()).hexdigest(),
                metadata={"cnmv_feed": feed_name},
            )
            items.append(item)
    except Exception:
        logger.exception("Error fetching CNMV feed %s", feed_name)
    return items


# Alias sync para compatibilidad con tests
fetch_cnmv_feed = _fetch_cnmv_feed_sync


async def fetch_cnmv_feed_async(feed_name: str, feed_url: str) -> list[NewsItem]:
    """Descarga un feed CNMV sin bloquear el event loop."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _fetch_cnmv_feed_sync, feed_name, feed_url)


async def fetch_all_cnmv() -> list[NewsItem]:
    """Descarga todos los feeds RSS de la CNMV configurados en paralelo."""
    tasks = [
        fetch_cnmv_feed_async(name, url)
        for name, url in config.CNMV_RSS_FEEDS.items()
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    all_items: list[NewsItem] = []
    for name, result in zip(config.CNMV_RSS_FEEDS.keys(), results):
        if isinstance(result, Exception):
            logger.exception("Error fetching CNMV %s: %s", name, result)
        else:
            all_items.extend(result)
            logger.info("  -> %d items from CNMV %s", len(result), name)
    return all_items
