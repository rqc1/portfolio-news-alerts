"""
Ingesta de noticias desde Alpha Vantage News Sentiment API.

Ventajas:
  - Noticias con tickers ya anotados (no hace falta NER para identificar empresa)
  - Score de sentimiento por ticker incluido en la respuesta
  - Texto del artículo y banderas de relevancia
  - Cobertura amplia de fuentes financieras US

Plan gratuito: 25 peticiones/día. Suficiente para un prototipo.
"""

import hashlib
import logging
from datetime import datetime, timezone

import httpx

import config
from modules.ingestion.models import NewsItem

logger = logging.getLogger(__name__)


async def fetch_alphavantage_news(
    tickers: list[str] | None = None,
    topics: list[str] | None = None,
    limit: int = 20,
) -> list[NewsItem]:
    """
    Obtiene noticias de Alpha Vantage News & Sentiments.

    topics posibles: earnings, ipo, mergers_and_acquisitions, financial_markets,
    economy_fiscal, economy_monetary, economy_macro, energy, finance,
    life_sciences, manufacturing, real_estate, retail_wholesale, technology
    """
    if not config.ALPHAVANTAGE_KEY:
        logger.warning("ALPHAVANTAGE_KEY no configurada, saltando Alpha Vantage")
        return []

    params = {
        "function": "NEWS_SENTIMENT",
        "apikey": config.ALPHAVANTAGE_KEY,
        "limit": min(limit, 200),
    }

    if tickers:
        params["tickers"] = ",".join(tickers)
    if topics:
        params["topics"] = ",".join(topics)

    items: list[NewsItem] = []
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(config.ALPHAVANTAGE_NEWS_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

            for article in data.get("feed", []):
                title = article.get("title", "")
                summary = article.get("summary", "")
                url = article.get("url", "")
                if not url or not title:
                    continue

                try:
                    time_str = article.get("time_published", "")
                    pub_dt = datetime.strptime(time_str, "%Y%m%dT%H%M%S").replace(
                        tzinfo=timezone.utc
                    )
                except (ValueError, TypeError):
                    pub_dt = datetime.now(timezone.utc)

                source_name = article.get("source", "alphavantage")
                full_text = f"{title} {summary}"

                # Alpha Vantage incluye tickers y sentimiento por ticker
                ticker_sentiments = article.get("ticker_sentiment", [])
                mentioned_tickers = [
                    ts.get("ticker", "") for ts in ticker_sentiments
                ]
                av_sentiment = article.get("overall_sentiment_label", "Neutral")

                item = NewsItem(
                    title=title,
                    summary=summary,
                    url=url,
                    source=f"alphavantage_{source_name}",
                    source_type="alphavantage",
                    published_at=pub_dt,
                    language="en",
                    author=", ".join(article.get("authors", [])),
                    content_hash=hashlib.sha256(full_text.encode()).hexdigest(),
                    entities_raw=mentioned_tickers,
                    metadata={
                        "av_sentiment": av_sentiment,
                        "av_sentiment_score": article.get(
                            "overall_sentiment_score", 0.0
                        ),
                        "ticker_sentiments": ticker_sentiments,
                        "topics": article.get("topics", []),
                        "banner_image": article.get("banner_image"),
                    },
                )
                items.append(item)

    except Exception:
        logger.exception("Error fetching Alpha Vantage news")

    return items
