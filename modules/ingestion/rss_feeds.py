"""
Ingesta de noticias desde feeds RSS genéricos.
"""

import asyncio
import hashlib
import logging
from datetime import datetime, timezone

import feedparser

from modules.ingestion.models import NewsItem

logger = logging.getLogger(__name__)


def _parse_date(entry) -> datetime:
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        from calendar import timegm
        return datetime.fromtimestamp(timegm(entry.published_parsed), tz=timezone.utc)
    return datetime.now(timezone.utc)


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _fetch_rss_feed_sync(feed_url: str, source_name: str) -> list[NewsItem]:
    """Descarga y parsea un feed RSS (bloqueante)."""
    items: list[NewsItem] = []
    try:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries:
            title = getattr(entry, "title", "")
            summary = getattr(entry, "summary", "")
            link = getattr(entry, "link", "")
            if not link:
                continue

            content = ""
            if hasattr(entry, "content") and entry.content:
                content = entry.content[0].get("value", "")

            full_text = f"{title} {summary} {content}"

            item = NewsItem(
                title=title,
                summary=summary,
                content=content,
                url=link,
                source=source_name,
                source_type="rss",
                published_at=_parse_date(entry),
                language="en",
                author=getattr(entry, "author", None),
                content_hash=_content_hash(full_text),
            )
            items.append(item)
    except Exception:
        logger.exception("Error fetching RSS feed %s", feed_url)

    return items


# Alias sync para compatibilidad con tests
fetch_rss_feed = _fetch_rss_feed_sync


async def fetch_rss_feed_async(feed_url: str, source_name: str) -> list[NewsItem]:
    """Descarga un feed RSS sin bloquear el event loop."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _fetch_rss_feed_sync, feed_url, source_name)


async def fetch_all_rss(feeds: dict[str, str]) -> list[NewsItem]:
    """Descarga todos los feeds RSS configurados en paralelo."""
    tasks = [
        fetch_rss_feed_async(url, name)
        for name, url in feeds.items()
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    all_items: list[NewsItem] = []
    for name, result in zip(feeds.keys(), results):
        if isinstance(result, Exception):
            logger.exception("Error fetching RSS %s: %s", name, result)
        else:
            all_items.extend(result)
            logger.info("  -> %d items from %s", len(result), name)
    return all_items
