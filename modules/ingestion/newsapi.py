"""
Ingesta de noticias desde NewsAPI.org.

Ventajas:
  - Texto completo de la noticia (no solo título + resumen)
  - +150.000 fuentes mundiales
  - Búsqueda por keyword, empresa, fecha, idioma y país
  - Metadatos ricos: source, author, publishedAt, urlToImage

Plan gratuito: 100 peticiones/día, noticias de hasta 1 mes atrás.
"""

import hashlib
import logging
from datetime import datetime, timezone

import httpx

import config
from modules.ingestion.models import NewsItem

logger = logging.getLogger(__name__)


async def search_newsapi(
    query: str,
    language: str = "en",
    sort_by: str = "publishedAt",
    page_size: int = 20,
) -> list[NewsItem]:
    """
    Busca noticias en NewsAPI.org por keyword.
    Requiere NEWSAPI_KEY en config.
    """
    if not config.NEWSAPI_KEY:
        logger.warning("NEWSAPI_KEY no configurada, saltando NewsAPI")
        return []

    params = {
        "q": query,
        "language": language,
        "sortBy": sort_by,
        "pageSize": min(page_size, 100),
        "apiKey": config.NEWSAPI_KEY,
    }

    items: list[NewsItem] = []
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(f"{config.NEWSAPI_BASE_URL}/everything", params=params)
            resp.raise_for_status()
            data = resp.json()

            if data.get("status") != "ok":
                logger.error("NewsAPI error: %s", data.get("message", ""))
                return []

            for article in data.get("articles", []):
                title = article.get("title", "") or ""
                description = article.get("description", "") or ""
                content = article.get("content", "") or ""
                url = article.get("url", "")
                if not url or not title:
                    continue

                try:
                    pub_dt = datetime.fromisoformat(
                        article["publishedAt"].replace("Z", "+00:00")
                    )
                except (KeyError, ValueError):
                    pub_dt = datetime.now(timezone.utc)

                source_name = article.get("source", {}).get("name", "newsapi")
                full_text = f"{title} {description} {content}"

                item = NewsItem(
                    title=title,
                    summary=description,
                    content=content,
                    url=url,
                    source=f"newsapi_{source_name}",
                    source_type="newsapi",
                    published_at=pub_dt,
                    language=language,
                    author=article.get("author"),
                    content_hash=hashlib.sha256(full_text.encode()).hexdigest(),
                    metadata={
                        "newsapi_source": source_name,
                        "image_url": article.get("urlToImage"),
                    },
                )
                items.append(item)

    except Exception:
        logger.exception("Error fetching NewsAPI")

    return items


async def search_newsapi_for_tickers(
    tickers: list[str],
    company_names: list[str],
    language: str = "en",
    page_size: int = 10,
) -> list[NewsItem]:
    """
    Busca noticias en NewsAPI para una lista de empresas.
    Combina ticker y nombre de empresa en la query.
    """
    all_items: list[NewsItem] = []
    # Agrupar en una sola query para no gastar peticiones
    query_parts = []
    for ticker, name in zip(tickers, company_names):
        query_parts.append(f'"{name}" OR "{ticker}"')

    # NewsAPI limita la query a ~500 chars
    query = " OR ".join(query_parts)
    if len(query) > 500:
        query = query[:500]

    items = await search_newsapi(query, language=language, page_size=page_size)
    all_items.extend(items)
    return all_items
