"""
API REST – FastAPI.

Endpoints para gestionar carteras, ingestar noticias y consultar alertas.
"""

import logging
import sys
from contextlib import asynccontextmanager
from typing import Optional

from bson import ObjectId
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Asegurar que el directorio raíz está en el path
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))

import config
from database.mongodb import MongoDB
from modules.portfolio.models import Portfolio, Asset
from modules.portfolio.service import PortfolioService
from modules.ingestion.service import IngestionService
from modules.alerts.engine import AlertEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Singleton del motor de alertas
alert_engine: Optional[AlertEngine] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global alert_engine
    await MongoDB.connect()
    alert_engine = AlertEngine()
    logger.info("System initialized: MongoDB connected, AlertEngine ready")
    yield
    await MongoDB.close()


app = FastAPI(
    title="Portfolio News Alert System",
    description="Sistema inteligente de alertas por noticias para carteras de inversión",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Schemas de request/response
# ---------------------------------------------------------------------------
class PortfolioCreate(BaseModel):
    user_id: str
    name: str = "Mi Cartera"
    assets: list[Asset] = []


class AssetAdd(BaseModel):
    ticker: str
    name: str
    isin: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    country: Optional[str] = None
    weight: float = 0.0
    aliases: list[str] = []


class ProcessNewsRequest(BaseModel):
    title: str
    summary: str = ""
    content: str = ""
    url: str = ""
    source: str = "manual"
    portfolio_id: str


# ---------------------------------------------------------------------------
# Endpoints – Portfolio
# ---------------------------------------------------------------------------
@app.post("/api/portfolios", tags=["Portfolio"])
async def create_portfolio(req: PortfolioCreate):
    portfolio = Portfolio(user_id=req.user_id, name=req.name, assets=req.assets)
    portfolio_id = await PortfolioService.create_portfolio(portfolio)
    return {"portfolio_id": portfolio_id}


@app.get("/api/portfolios/{portfolio_id}", tags=["Portfolio"])
async def get_portfolio(portfolio_id: str):
    portfolio = await PortfolioService.get_portfolio(portfolio_id)
    if portfolio is None:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return portfolio


@app.get("/api/portfolios", tags=["Portfolio"])
async def list_portfolios(user_id: str = Query(...)):
    portfolios = await PortfolioService.get_portfolios_by_user(user_id)
    return portfolios


@app.post("/api/portfolios/{portfolio_id}/assets", tags=["Portfolio"])
async def add_asset(portfolio_id: str, req: AssetAdd):
    asset = Asset(**req.model_dump())
    ok = await PortfolioService.add_asset(portfolio_id, asset)
    if not ok:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return {"status": "ok"}


@app.delete("/api/portfolios/{portfolio_id}/assets/{ticker}", tags=["Portfolio"])
async def remove_asset(portfolio_id: str, ticker: str):
    ok = await PortfolioService.remove_asset(portfolio_id, ticker)
    if not ok:
        raise HTTPException(status_code=404, detail="Portfolio or asset not found")
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Endpoints – Ingestion
# ---------------------------------------------------------------------------
@app.post("/api/ingest", tags=["Ingestion"])
async def ingest_all(query: str = "", tickers: str = ""):
    ticker_list = [t.strip() for t in tickers.split(",") if t.strip()] if tickers else None
    stats = await IngestionService.ingest_all(query=query, tickers=ticker_list)
    return {"status": "ok", "stats": stats}


@app.post("/api/ingest/rss", tags=["Ingestion"])
async def ingest_rss():
    count = await IngestionService.ingest_rss_only()
    return {"status": "ok", "count": count}


@app.post("/api/ingest/cnmv", tags=["Ingestion"])
async def ingest_cnmv():
    count = await IngestionService.ingest_cnmv_only()
    return {"status": "ok", "count": count}


@app.post("/api/ingest/newsapi", tags=["Ingestion"])
async def ingest_newsapi(query: str = Query(...), language: str = "en"):
    count = await IngestionService.ingest_newsapi(query, language=language)
    return {"status": "ok", "count": count}


@app.post("/api/ingest/alphavantage", tags=["Ingestion"])
async def ingest_alphavantage(tickers: str = Query(...)):
    ticker_list = [t.strip() for t in tickers.split(",") if t.strip()]
    count = await IngestionService.ingest_alphavantage(ticker_list)
    return {"status": "ok", "count": count}


@app.get("/api/news", tags=["Ingestion"])
async def list_news(limit: int = Query(50, ge=1, le=200)):
    news = await IngestionService.get_recent_news(limit=limit)
    for item in news:
        item["_id"] = str(item["_id"])
    return news


# ---------------------------------------------------------------------------
# Endpoints – Alerts
# ---------------------------------------------------------------------------
@app.post("/api/alerts/process", tags=["Alerts"])
async def process_single_news(req: ProcessNewsRequest):
    portfolio_doc = await PortfolioService.get_portfolio(req.portfolio_id)
    if portfolio_doc is None:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    portfolio_doc.pop("_id", None)
    portfolio = Portfolio(**portfolio_doc)

    alert = await alert_engine.process_and_store(
        title=req.title,
        summary=req.summary,
        content=req.content,
        url=req.url,
        source=req.source,
        portfolio=portfolio,
        portfolio_id=req.portfolio_id,
    )

    if alert is None:
        return {"status": "no_alert", "reason": "Below relevance or severity threshold"}

    return {
        "status": "alert_generated",
        "alert": alert.model_dump(),
    }


@app.post("/api/alerts/process-batch/{portfolio_id}", tags=["Alerts"])
async def process_batch(portfolio_id: str, limit: int = Query(50, ge=1, le=200)):
    """Procesa las noticias recientes contra una cartera."""
    portfolio_doc = await PortfolioService.get_portfolio(portfolio_id)
    if portfolio_doc is None:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    portfolio_doc.pop("_id", None)
    portfolio = Portfolio(**portfolio_doc)

    news_items = await IngestionService.get_recent_news(limit=limit)
    results = {"processed": 0, "alerts_generated": 0, "duplicates": 0, "discarded": 0}

    for item in news_items:
        results["processed"] += 1
        alert = await alert_engine.process_and_store(
            title=item.get("title", ""),
            summary=item.get("summary", ""),
            content=item.get("content", ""),
            url=item.get("url", ""),
            source=item.get("source", ""),
            portfolio=portfolio,
            portfolio_id=portfolio_id,
            news_id=str(item.get("_id", "")),
        )
        if alert is None:
            results["discarded"] += 1
        elif alert.is_duplicate:
            results["duplicates"] += 1
        else:
            results["alerts_generated"] += 1

    return results


@app.get("/api/alerts", tags=["Alerts"])
async def list_alerts(
    portfolio_id: str = Query(""),
    limit: int = Query(50, ge=1, le=200),
):
    query = {}
    if portfolio_id:
        query["portfolio_id"] = portfolio_id

    cursor = MongoDB.alerts().find(query).sort("created_at", -1).limit(limit)
    alerts = await cursor.to_list(length=limit)
    for a in alerts:
        a["_id"] = str(a["_id"])
    return alerts


@app.get("/api/alerts/stats", tags=["Alerts"])
async def alert_stats(portfolio_id: str = Query("")):
    query = {}
    if portfolio_id:
        query["portfolio_id"] = portfolio_id

    pipeline = [
        {"$match": query},
        {
            "$group": {
                "_id": None,
                "total": {"$sum": 1},
                "avg_severity": {"$avg": "$severity"},
                "avg_confidence": {"$avg": "$confidence"},
            }
        },
    ]
    result = await MongoDB.alerts().aggregate(pipeline).to_list(length=1)
    if result:
        stats = result[0]
        stats.pop("_id", None)
        return stats
    return {"total": 0, "avg_severity": 0.0, "avg_confidence": 0.0}


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host=config.API_HOST, port=config.API_PORT, reload=True)
