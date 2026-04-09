"""
Ingesta de noticias desde feeds RSS de la CNMV.
"""

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


def fetch_cnmv_feed(feed_name: str, feed_url: str) -> list[NewsItem]:
    """Descarga un feed RSS de la CNMV."""
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


def fetch_all_cnmv() -> list[NewsItem]:
    """Descarga todos los feeds RSS de la CNMV configurados."""
    all_items: list[NewsItem] = []
    for name, url in config.CNMV_RSS_FEEDS.items():
        logger.info("Fetching CNMV: %s", name)
        items = fetch_cnmv_feed(name, url)
        all_items.extend(items)
        logger.info("  -> %d items from CNMV %s", len(items), name)
    return all_items
