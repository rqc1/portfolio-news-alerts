"""
Ingesta de filings y noticias desde SEC EDGAR.
"""

import hashlib
import logging
from datetime import datetime, timezone

import httpx

import config
from modules.ingestion.models import NewsItem

logger = logging.getLogger(__name__)

HEADERS = {"User-Agent": config.SEC_USER_AGENT, "Accept": "application/json"}


async def search_recent_filings(
    query: str = "",
    form_types: list[str] | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 20,
) -> list[NewsItem]:
    """
    Busca filings recientes en EDGAR full-text search.
    https://efts.sec.gov/LATEST/search-index?q=...&dateRange=custom&startdt=...&enddt=...&forms=8-K
    """
    params: dict = {"q": query}
    if form_types:
        params["forms"] = ",".join(form_types)
    if start_date:
        params["dateRange"] = "custom"
        params["startdt"] = start_date
    if end_date:
        params["enddt"] = end_date

    items: list[NewsItem] = []
    try:
        async with httpx.AsyncClient(headers=HEADERS, timeout=30) as client:
            resp = await client.get(
                "https://efts.sec.gov/LATEST/search-index",
                params=params,
            )
            resp.raise_for_status()
            data = resp.json()

            hits = data.get("hits", {}).get("hits", [])
            for hit in hits[:limit]:
                src = hit.get("_source", {})
                file_date = src.get("file_date", "")
                try:
                    pub_dt = datetime.strptime(file_date, "%Y-%m-%d").replace(
                        tzinfo=timezone.utc
                    )
                except (ValueError, TypeError):
                    pub_dt = datetime.now(timezone.utc)

                title = f"[{src.get('form_type', 'Filing')}] {src.get('display_names', [''])[0]}"
                url = f"https://www.sec.gov/Archives/edgar/data/{src.get('entity_id', '')}/{src.get('file_num', '')}"

                item = NewsItem(
                    title=title,
                    summary=src.get("file_description", ""),
                    url=url,
                    source="sec_edgar",
                    source_type="sec_edgar",
                    published_at=pub_dt,
                    language="en",
                    content_hash=hashlib.sha256(url.encode()).hexdigest(),
                    metadata={
                        "form_type": src.get("form_type"),
                        "cik": src.get("entity_id"),
                        "company": src.get("display_names", []),
                    },
                )
                items.append(item)

    except Exception:
        logger.exception("Error searching SEC EDGAR")

    return items


async def get_company_filings(cik: str, limit: int = 10) -> list[NewsItem]:
    """
    Obtiene los filings recientes de una compañía por su CIK.
    """
    cik_padded = cik.zfill(10)
    url = config.SEC_EDGAR_SUBMISSIONS.format(cik=cik_padded)
    items: list[NewsItem] = []

    try:
        async with httpx.AsyncClient(headers=HEADERS, timeout=30) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()

            recent = data.get("filings", {}).get("recent", {})
            forms = recent.get("form", [])
            dates = recent.get("filingDate", [])
            accessions = recent.get("accessionNumber", [])
            descriptions = recent.get("primaryDocDescription", [])

            company_name = data.get("name", "Unknown")

            for i in range(min(limit, len(forms))):
                try:
                    pub_dt = datetime.strptime(dates[i], "%Y-%m-%d").replace(
                        tzinfo=timezone.utc
                    )
                except (ValueError, IndexError):
                    pub_dt = datetime.now(timezone.utc)

                acc = accessions[i].replace("-", "") if i < len(accessions) else ""
                filing_url = f"https://www.sec.gov/Archives/edgar/data/{cik_padded}/{acc}"

                item = NewsItem(
                    title=f"[{forms[i]}] {company_name}",
                    summary=descriptions[i] if i < len(descriptions) else "",
                    url=filing_url,
                    source="sec_edgar",
                    source_type="sec_edgar",
                    published_at=pub_dt,
                    language="en",
                    content_hash=hashlib.sha256(filing_url.encode()).hexdigest(),
                    metadata={
                        "form_type": forms[i],
                        "cik": cik,
                        "company": company_name,
                    },
                )
                items.append(item)

    except Exception:
        logger.exception("Error fetching SEC EDGAR filings for CIK %s", cik)

    return items
