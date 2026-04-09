"""
Ingesta de noticias desde feeds RSS genéricos.
"""

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


def fetch_rss_feed(feed_url: str, source_name: str) -> list[NewsItem]:
    """Descarga y parsea un feed RSS, devolviendo una lista de NewsItem."""
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


def fetch_all_rss(feeds: dict[str, str]) -> list[NewsItem]:
    """Descarga todos los feeds RSS configurados."""
    all_items: list[NewsItem] = []
    for name, url in feeds.items():
        logger.info("Fetching RSS: %s", name)
        items = fetch_rss_feed(url, source_name=name)
        all_items.extend(items)
        logger.info("  -> %d items from %s", len(items), name)
    return all_items
