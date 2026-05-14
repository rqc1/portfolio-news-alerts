"""Tests para módulo Ingestion (models)."""

from datetime import datetime, timezone

from modules.ingestion.models import NewsItem


class TestNewsItem:
    def test_create_minimal(self):
        item = NewsItem(title="Test headline", url="https://example.com/1", source="rss")
        assert item.title == "Test headline"
        assert item.source == "rss"
        assert item.source_type == "rss"
        assert item.language == "en"
        assert isinstance(item.published_at, datetime)

    def test_create_full(self):
        item = NewsItem(
            title="Apple earnings",
            summary="Apple reported record results",
            content="Full article content here...",
            url="https://reuters.com/apple",
            source="reuters_business",
            source_type="rss",
            language="en",
            author="John Doe",
            content_hash="abc123",
            entities_raw=["Apple Inc.", "iPhone"],
            metadata={"feed": "reuters"},
        )
        assert item.author == "John Doe"
        assert item.content_hash == "abc123"
        assert len(item.entities_raw) == 2
        assert item.metadata["feed"] == "reuters"

    def test_model_dump(self):
        item = NewsItem(title="Test", url="https://example.com", source="test")
        d = item.model_dump()
        assert "title" in d
        assert "url" in d
        assert "source" in d
        assert "published_at" in d
        assert "ingested_at" in d
