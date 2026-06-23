"""
API REST – FastAPI.

Endpoints para gestionar carteras, ingestar noticias y consultar alertas.
"""

import asyncio
import concurrent.futures
import logging
import sys
import time
import uuid
from contextlib import asynccontextmanager
from typing import Optional

from bson import ObjectId
from fastapi import FastAPI, BackgroundTasks, HTTPException, Query, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

# Asegurar que el directorio raíz está en el path
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))

import config
from database.mongodb import MongoDB
from modules.portfolio.models import Portfolio, Asset
from modules.portfolio.service import PortfolioService
from modules.ingestion.service import IngestionService
from modules.alerts.engine import AlertEngine
from modules.scheduler.service import start_scheduler, stop_scheduler, get_scheduler_status
from modules.notifications.service import NotificationService
from modules.advisor.service import AdvisorService
from modules.advisor.models import QuestionnaireAnswer
from modules.market.service import MarketService
from modules.analytics.service import AnalyticsService
from modules.backtest.service import (
    AlertBacktestService,
    AlertFeedback,
    FeedbackService,
)
from modules.security.auth import (
    AuthService,
    CurrentUser,
    TokenResponse,
    UserCreate,
    UserPublic,
    create_access_token,
    get_current_user,
)
from modules.security.logging_config import configure_logging
from modules.security import metrics as obs_metrics

# Logging estructurado (JSON en producción si LOG_JSON=true).
configure_logging(json_logs=config.LOG_JSON, level=config.LOG_LEVEL)
logging.basicConfig(level=getattr(logging, config.LOG_LEVEL, logging.INFO))
logger = logging.getLogger(__name__)

# Singleton del motor de alertas
alert_engine: Optional[AlertEngine] = None


def _preload_models():
    """Carga todos los modelos ML en memoria (bloqueante, ejecutar en thread)."""
    from modules.nlp.preprocessing import _load_spacy
    from modules.events.classifier import _load_finbert, _load_nli_pipeline
    from modules.relevance.service import _load_embedding_model
    logger.info("Preloading ML models...")
    _load_spacy()
    _load_finbert()
    _load_nli_pipeline()
    _load_embedding_model()
    logger.info("All ML models loaded")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global alert_engine
    await MongoDB.connect()

    # En cloud mode no cargamos modelos ML locales (ahorra ~2GB RAM)
    if not config.CLOUD_MODE:
        loop = asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            await loop.run_in_executor(pool, _preload_models)
    else:
        logger.info("CLOUD_MODE=true: skipping local ML model preload (using LLM instead)")

    alert_engine = AlertEngine()
    start_scheduler(alert_engine)
    logger.info("System initialized: MongoDB connected, AlertEngine ready, Scheduler started")
    yield
    stop_scheduler()
    await MongoDB.close()


app = FastAPI(
    title="InvestAIlert API",
    description="Sistema inteligente de alertas por noticias para carteras de inversión",
    version="0.1.0",
    lifespan=lifespan,
)

# --- Rate limiting (slowapi) ---
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[config.RATE_LIMIT_DEFAULT] if config.RATE_LIMIT_ENABLED else [],
    enabled=config.RATE_LIMIT_ENABLED,
)
app.state.limiter = limiter


async def _rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return Response(
        content='{"detail":"Rate limit exceeded"}',
        status_code=429,
        media_type="application/json",
    )


app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)
app.add_middleware(SlowAPIMiddleware)

# --- CORS desde configuración (restringible por entorno) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Middleware de observabilidad: request_id + logging + métricas ---
@app.middleware("http")
async def observability_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    start = time.perf_counter()
    try:
        import structlog
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )
    except Exception:  # noqa: BLE001
        pass

    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        duration = time.perf_counter() - start
        # Usar la plantilla de ruta para evitar explosión de cardinalidad.
        route = request.scope.get("route")
        path_label = getattr(route, "path", request.url.path)
        if config.METRICS_ENABLED:
            try:
                obs_metrics.record_http(request.method, path_label, status_code, duration)
            except Exception:  # noqa: BLE001
                pass
        logger.info(
            "request",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status": status_code,
                "duration_ms": round(duration * 1000, 2),
            },
        )
        try:
            import structlog
            structlog.contextvars.clear_contextvars()
        except Exception:  # noqa: BLE001
            pass


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


class AdvisorAnswerItem(BaseModel):
    question_id: str
    selected_option_id: str


class AdvisorSubmission(BaseModel):
    user_id: str
    portfolio_id: str
    answers: list[AdvisorAnswerItem]


class AlertFeedbackRequest(BaseModel):
    alert_id: str
    useful: bool
    user_id: str = "default"
    comment: str = ""


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
# Endpoints – Feedback loop & Backtesting (validación predictiva)
# ---------------------------------------------------------------------------
@app.post("/api/alerts/feedback", tags=["Backtesting"])
async def submit_alert_feedback(req: AlertFeedbackRequest):
    """Registra la valoración del usuario (útil / no útil) sobre una alerta.

    Estas señales alimentan el bucle de mejora continua: medir la precisión
    percibida y, a futuro, reentrenar / recalibrar el sistema.
    """
    feedback = AlertFeedback(
        alert_id=req.alert_id,
        user_id=req.user_id,
        useful=req.useful,
        comment=req.comment,
    )
    await FeedbackService.record(feedback)
    return {"status": "ok"}


@app.get("/api/alerts/feedback/stats", tags=["Backtesting"])
async def get_feedback_stats(portfolio_id: str = Query("")):
    """Estadísticos agregados del feedback (tasa de utilidad)."""
    return await FeedbackService.stats(portfolio_id)


@app.post("/api/backtest/{portfolio_id}", tags=["Backtesting"])
async def run_backtest(
    portfolio_id: str,
    limit: int = Query(100, ge=1, le=500),
    persist: bool = Query(True),
    current: CurrentUser = Depends(get_current_user),
):
    """Backtesting de las alertas almacenadas contra el retorno anormal real.

    Para cada alerta con ticker y fecha, ejecuta un estudio de eventos (CAR)
    y agrega: hit-rate direccional, CAR medio y CAR por severidad. Operación
    potencialmente lenta (descarga precios de mercado).
    """
    try:
        result = await AlertBacktestService.backtest(
            portfolio_id=portfolio_id, limit=limit, persist=persist
        )
    except Exception as exc:  # noqa: BLE001 — frontera de sistema
        logger.exception("Backtest failed")
        raise HTTPException(status_code=500, detail=f"Backtest error: {exc}")
    # No exponer los pares internos de calibración.
    result.pop("_calibration_pairs", None)
    return result


@app.post("/api/backtest/{portfolio_id}/calibrate", tags=["Backtesting"])
async def fit_severity_calibrator(
    portfolio_id: str,
    limit: int = Query(500, ge=1, le=1000),
    current: CurrentUser = Depends(get_current_user),
):
    """Ajusta el calibrador de severidad con datos empíricos de backtesting.

    Recolecta pares (severidad predicha, |CAR| observado) y ajusta una
    regresión isotónica que ancla la severidad al movimiento real de precio.
    """
    try:
        result = await AlertBacktestService.fit_calibrator(
            portfolio_id=portfolio_id,
            limit=limit,
            save_path=config.SEVERITY_CALIBRATOR_PATH,
        )
    except Exception as exc:  # noqa: BLE001 — frontera de sistema
        logger.exception("Calibrator fit failed")
        raise HTTPException(status_code=500, detail=f"Calibration error: {exc}")
    return result


# ---------------------------------------------------------------------------
# Endpoints – Autenticación
# ---------------------------------------------------------------------------
@app.post("/api/auth/register", tags=["Auth"], response_model=UserPublic)
async def register_user(data: UserCreate):
    """Registra un nuevo usuario (email + contraseña hasheada con bcrypt)."""
    return await AuthService.register(data)


@app.post("/api/auth/login", tags=["Auth"], response_model=TokenResponse)
async def login(form: OAuth2PasswordRequestForm = Depends()):
    """Autentica y emite un JWT. `username` = email."""
    user = await AuthService.authenticate(form.username, form.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    token, expires_in = create_access_token(str(user["_id"]), user.get("email", ""))
    return TokenResponse(access_token=token, expires_in=expires_in)


@app.get("/api/auth/me", tags=["Auth"])
async def whoami(current: CurrentUser = Depends(get_current_user)):
    """Devuelve la identidad autenticada (o anónima si AUTH_ENABLED=false)."""
    return current.model_dump()



# ---------------------------------------------------------------------------
# Endpoints – Advisor (Asesor de inversiones)
# ---------------------------------------------------------------------------
@app.get("/api/advisor/questions", tags=["Advisor"])
async def get_advisor_questions():
    """Devuelve el cuestionario completo para perfilar al inversor."""
    questions = AdvisorService.get_questions()
    return [q.model_dump() for q in questions]


@app.post("/api/advisor/profile", tags=["Advisor"])
async def compute_investor_profile(req: AdvisorSubmission):
    """Calcula el perfil del inversor a partir de las respuestas del cuestionario."""
    answers = [QuestionnaireAnswer(question_id=a.question_id,
                                   selected_option_id=a.selected_option_id)
               for a in req.answers]
    profile = AdvisorService.compute_profile(req.user_id, req.portfolio_id, answers)
    return profile.model_dump()


@app.post("/api/advisor/report", tags=["Advisor"])
async def generate_advisor_report(req: AdvisorSubmission):
    """Genera un informe completo: perfil + análisis + recomendaciones."""
    # Verificar que la cartera existe
    portfolio_doc = await PortfolioService.get_portfolio(req.portfolio_id)
    if portfolio_doc is None:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    portfolio_doc.pop("_id", None)
    portfolio = Portfolio(**portfolio_doc)

    # Calcular perfil
    answers = [QuestionnaireAnswer(question_id=a.question_id,
                                   selected_option_id=a.selected_option_id)
               for a in req.answers]
    profile = AdvisorService.compute_profile(req.user_id, req.portfolio_id, answers)

    # Generar informe
    report = await AdvisorService.generate_report(profile, portfolio)

    # Guardar en MongoDB
    report_id = await AdvisorService.save_report(report)

    result = report.model_dump()
    result["_id"] = report_id
    return result


@app.get("/api/advisor/reports/{portfolio_id}", tags=["Advisor"])
async def list_advisor_reports(portfolio_id: str, limit: int = Query(10, ge=1, le=50)):
    """Obtiene los informes de asesoramiento previos de una cartera."""
    reports = await AdvisorService.get_reports_by_portfolio(portfolio_id, limit=limit)
    return reports


# ---------------------------------------------------------------------------
# Endpoints – Market Data (yfinance)
# ---------------------------------------------------------------------------
@app.get("/api/market/lookup/{ticker}", tags=["Market"])
async def lookup_ticker(ticker: str):
    """Busca información de un activo por ticker (auto-fill)."""
    result = MarketService.lookup_ticker(ticker)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Ticker '{ticker}' not found")
    return result.model_dump()


@app.get("/api/market/price/{ticker}", tags=["Market"])
async def get_price(ticker: str):
    """Obtiene precio actual y variación diaria de un ticker."""
    snap = MarketService.get_price(ticker)
    if snap is None:
        raise HTTPException(status_code=404, detail=f"Price not available for '{ticker}'")
    return snap.model_dump()


@app.post("/api/market/prices", tags=["Market"])
async def get_prices_batch(tickers: list[str]):
    """Obtiene precios para múltiples tickers."""
    results = MarketService.get_prices_batch(tickers)
    return {k: v.model_dump() for k, v in results.items()}


@app.get("/api/market/history/{ticker}", tags=["Market"])
async def get_history(ticker: str, period: str = Query("1y")):
    """Obtiene histórico de precios OHLCV."""
    data = MarketService.get_history(ticker, period=period)
    return {"ticker": ticker, "period": period, "data": data}


# ---------------------------------------------------------------------------
# Endpoints – Portfolio Analytics (quantstats)
# ---------------------------------------------------------------------------
@app.get("/api/analytics/{portfolio_id}", tags=["Analytics"])
async def get_portfolio_analytics(
    portfolio_id: str,
    period: str = Query("1y"),
    benchmark: str = Query("SPY"),
):
    """Calcula métricas de rendimiento y riesgo de una cartera."""
    portfolio_doc = await PortfolioService.get_portfolio(portfolio_id)
    if portfolio_doc is None:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    portfolio_doc.pop("_id", None)
    portfolio = Portfolio(**portfolio_doc)

    tickers = portfolio.get_tickers()
    weights = [a.weight for a in portfolio.assets]
    if not tickers or not any(w > 0 for w in weights):
        raise HTTPException(status_code=400, detail="Portfolio has no assets with weights")

    result = AnalyticsService.compute_metrics(tickers, weights, period=period, benchmark=benchmark)
    if result is None:
        raise HTTPException(status_code=404, detail="Could not compute analytics (no market data)")
    return result.model_dump()


# ---------------------------------------------------------------------------
# Health & Observabilidad
# ---------------------------------------------------------------------------
@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/health/live", tags=["System"])
async def health_live():
    """Liveness probe: el proceso responde."""
    return {"status": "alive"}


@app.get("/health/ready", tags=["System"])
async def health_ready():
    """Readiness probe: dependencias críticas (DB) disponibles."""
    db_ok = await _db_ping()
    status_code = 200 if db_ok else 503
    return Response(
        content='{"status":"%s","db":%s}' % ("ready" if db_ok else "not_ready",
                                             "true" if db_ok else "false"),
        status_code=status_code,
        media_type="application/json",
    )


@app.get("/health/db", tags=["System"])
async def health_db():
    """Comprueba la conectividad con MongoDB."""
    db_ok = await _db_ping()
    if not db_ok:
        raise HTTPException(status_code=503, detail="Database unavailable")
    return {"status": "ok", "db": "up"}


async def _db_ping() -> bool:
    try:
        await MongoDB._client.admin.command("ping")
        return True
    except Exception:  # noqa: BLE001
        logger.warning("DB ping failed", exc_info=True)
        return False


@app.get("/metrics", tags=["System"])
async def metrics():
    """Métricas en formato de exposición Prometheus."""
    if not config.METRICS_ENABLED:
        raise HTTPException(status_code=404, detail="Metrics disabled")
    payload, content_type = obs_metrics.render_latest()
    return Response(content=payload, media_type=content_type)


# ---------------------------------------------------------------------------
# Trigger pipeline (para cron externo: cron-job.org, UptimeRobot, etc.)
# ---------------------------------------------------------------------------
@app.post("/api/trigger-pipeline", tags=["System"])
async def trigger_pipeline(background_tasks: BackgroundTasks, token: str = Query("")):
    """
    Ejecuta el pipeline completo en background: ingestar RSS → procesar alertas.
    Devuelve 202 inmediatamente para evitar timeouts de cron-job.org.
    Protegido con un token simple para evitar ejecuciones no autorizadas.
    """
    expected_token = config.CRON_SECRET
    if expected_token and token != expected_token:
        raise HTTPException(status_code=403, detail="Invalid token")

    background_tasks.add_task(_run_pipeline)
    return {"status": "accepted", "message": "Pipeline started in background"}


async def _run_pipeline():
    """Ejecuta el pipeline completo de ingestión y alertas."""
    import logging
    logger = logging.getLogger(__name__)
    try:
        from modules.ingestion.service import IngestionService
        from modules.portfolio.service import PortfolioService

        # 1. Ingestar noticias RSS
        rss_count = await IngestionService.ingest_rss_only()
        logger.info(f"Pipeline: RSS ingested = {rss_count}")

        # 2. Procesar alertas para todas las carteras
        all_portfolios = await PortfolioService.get_all_portfolios()
        total_alerts = 0

        for pdoc in all_portfolios:
            pid = str(pdoc.pop("_id", ""))
            portfolio = Portfolio(**pdoc)
            news_items = await IngestionService.get_recent_news(limit=100)

            for item in news_items:
                alert = await alert_engine.process_and_store(
                    title=item.get("title", ""),
                    summary=item.get("summary", ""),
                    content=item.get("content", ""),
                    url=item.get("url", ""),
                    source=item.get("source", ""),
                    portfolio=portfolio,
                    portfolio_id=pid,
                    news_id=str(item.get("_id", "")),
                )
                if alert and not alert.is_duplicate:
                    total_alerts += 1

        logger.info(f"Pipeline complete: {len(all_portfolios)} portfolios, {total_alerts} alerts")
    except Exception as e:
        logger.error(f"Pipeline error: {e}")


# ---------------------------------------------------------------------------
# System status (scheduler + notifications)
# ---------------------------------------------------------------------------
@app.get("/api/system/status", tags=["System"])
async def system_status():
    return {
        "scheduler": get_scheduler_status(),
        "notifications": NotificationService.get_status(),
    }


# ---------------------------------------------------------------------------
# Endpoints – Model Comparison
# ---------------------------------------------------------------------------
@app.get("/api/comparisons", tags=["Comparisons"])
async def get_model_comparisons(limit: int = Query(5)):
    """Devuelve las últimas comparaciones multi-modelo."""
    col = MongoDB.db()["model_comparisons"]
    cursor = col.find({}, {"results": 0}).sort("timestamp", -1).limit(limit)
    docs = await cursor.to_list(length=limit)
    for d in docs:
        d["_id"] = str(d["_id"])
    return docs


@app.get("/api/comparisons/latest", tags=["Comparisons"])
async def get_latest_comparison():
    """Devuelve la comparación más reciente con detalle completo."""
    col = MongoDB.db()["model_comparisons"]
    doc = await col.find_one(sort=[("timestamp", -1)])
    if not doc:
        raise HTTPException(status_code=404, detail="No comparisons found")
    doc["_id"] = str(doc["_id"])
    return doc


if __name__ == "__main__":
    import os
    import uvicorn

    uvicorn.run(
        "main:app",
        host=config.API_HOST,
        port=config.API_PORT,
        reload=os.getenv("UVICORN_RELOAD", "false").lower() == "true",
    )
