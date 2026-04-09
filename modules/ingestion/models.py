"""
Modelos de datos para noticias ingestadas.
"""

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class NewsItem(BaseModel):
    title: str
    summary: str = ""
    content: str = ""
    url: str
    source: str
    source_type: str = Field(
        default="rss", description="rss | sec_edgar | cnmv | api"
    )
    published_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    language: str = "en"
    author: Optional[str] = None
    content_hash: str = ""
    entities_raw: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)
    ingested_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
