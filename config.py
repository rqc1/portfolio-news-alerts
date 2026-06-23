"""
Configuración central del sistema de alertas inteligentes para carteras de inversión.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(override=True)  # Carga .env antes de leer variables (override=sistema)

# ---------------------------------------------------------------------------
# Rutas
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"

# ---------------------------------------------------------------------------
# MongoDB
# ---------------------------------------------------------------------------
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "portfolio_alerts")

# ---------------------------------------------------------------------------
# NLP – FinBERT (sentiment)
# ---------------------------------------------------------------------------
FINBERT_MODEL = os.getenv("FINBERT_MODEL", "ProsusAI/finbert")
SPACY_MODEL = os.getenv("SPACY_MODEL", "en_core_web_sm")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

# ---------------------------------------------------------------------------
# LLM (OpenAI / Azure OpenAI) – legacy, usado por OPENAI_API_KEY resolver
# ---------------------------------------------------------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# ---------------------------------------------------------------------------
# LLM Multi-proveedor – análisis contextual de impacto y explicaciones
# ---------------------------------------------------------------------------
# Proveedores: "openai", "github", "huggingface", "ollama"
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "github")
LLM_MODEL = os.getenv("LLM_MODEL", "")         # vacío = default del proveedor
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "")    # vacío = default del proveedor
LLM_API_KEY = os.getenv("LLM_API_KEY", "")      # vacío = resuelve por proveedor

# GitHub Models (gratuito con GITHUB_TOKEN)
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

# HuggingFace Inference API (tier gratuito con HF_TOKEN)
HF_TOKEN = os.getenv("HF_TOKEN", "")

# ---------------------------------------------------------------------------
# NLI – Zero-shot classification (reemplaza LLM para tipo de evento)
# ---------------------------------------------------------------------------
NLI_MODEL = os.getenv("NLI_MODEL", "facebook/bart-large-mnli")

# ---------------------------------------------------------------------------
# Fuentes de datos
# ---------------------------------------------------------------------------
SEC_EDGAR_BASE_URL = "https://efts.sec.gov/LATEST/search-index"
SEC_EDGAR_COMPANY_TICKERS = "https://www.sec.gov/files/company_tickers.json"
SEC_EDGAR_SUBMISSIONS = "https://data.sec.gov/submissions/CIK{cik}.json"
SEC_USER_AGENT = os.getenv("SEC_USER_AGENT", "TFM-Alertas rquerol@example.com")

CNMV_RSS_FEEDS = {
    "hechos_relevantes": "https://www.cnmv.es/Portal/Publicaciones/RSSHechosRelev.aspx",
    "informacion_privilegiada": "https://www.cnmv.es/Portal/Publicaciones/RSSInfoPrivilegiada.aspx",
    "notas_prensa": "https://www.cnmv.es/Portal/Publicaciones/RSSNotasPrensa.aspx",
}

RSS_FEEDS = {
    # --- Noticias financieras generales ---
    "reuters_business": "https://feeds.reuters.com/reuters/businessNews",
    "yahoo_finance": "https://finance.yahoo.com/news/rssindex",
    "financial_times": "https://www.ft.com/rss/home",
    "seeking_alpha": "https://seekingalpha.com/market_currents.xml",
    "investing_com": "https://www.investing.com/rss/news.rss",
    "investing_com_stocks": "https://www.investing.com/rss/news_301.rss",
    "marketwatch": "https://feeds.content.dowjones.io/public/rss/mw_topstories",
    "cnbc_finance": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664",
    "cnbc_tech": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=19854910",
    # --- Tecnología y semiconductores ---
    "techcrunch": "https://techcrunch.com/feed/",
    "ars_technica": "https://feeds.arstechnica.com/arstechnica/technology-lab",
    "tomshardware": "https://www.tomshardware.com/feeds/all",
    "semianalysis_blog": "https://www.semianalysis.com/feed",
    # --- Oro y materias primas ---
    "mining_com": "https://www.mining.com/feed/",
    # --- Macroeconomía y bancos centrales ---
    "ecb_press": "https://www.ecb.europa.eu/rss/press.html",
    "fed_press": "https://www.federalreserve.gov/feeds/press_all.xml",
    "boe_news": "https://www.bankofengland.co.uk/rss/news",
    "imf_news": "https://www.imf.org/en/News/rss",
    # --- Prensa financiera española ---
    "expansion": "https://e00-expansion.uecdn.es/rss/portada.xml",
    "cinco_dias": "https://cincodias.elpais.com/rss/mercados/portada.xml",
    "el_economista": "https://www.eleconomista.es/rss/rss-mercados.php",
    # --- Ciberseguridad ---
    "bleeping_computer": "https://www.bleepingcomputer.com/feed/",
    "the_hacker_news": "https://feeds.feedburner.com/TheHackersNews",
    "security_week": "https://feeds.feedburner.com/securityweek",
    # --- Cadena de suministro y logística ---
    "supply_chain_dive": "https://www.supplychaindive.com/feeds/news/",
    "freightwaves": "https://www.freightwaves.com/news/feed",
}

# --- API de noticias enriquecidas (texto completo + metadata) ---
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "")
NEWSAPI_BASE_URL = "https://newsapi.org/v2"
ALPHAVANTAGE_KEY = os.getenv("ALPHAVANTAGE_KEY", "")
ALPHAVANTAGE_NEWS_URL = "https://www.alphavantage.co/query"

# ---------------------------------------------------------------------------
# Taxonomía de eventos
# ---------------------------------------------------------------------------
EVENT_TAXONOMY = [
    "resultados_empresariales",
    "guidance_profit_warning",
    "regulacion",
    "litigio",
    "fusion_adquisicion",
    "ciberincidente",
    "incidencia_operativa",
    "macroeconomia",
    "cadena_suministro",
    "cambio_directivo",
    "dividendo_recompra",
    "otro",
]

# ---------------------------------------------------------------------------
# Motor de alertas – umbrales
# ---------------------------------------------------------------------------
ALERT_RELEVANCE_THRESHOLD = 0.5      # mínimo para pasar (sin LLM)
ALERT_RELEVANCE_BORDERLINE = 0.3     # entre borderline y threshold → LLM decide
ALERT_SEVERITY_THRESHOLD = 0.3
ALERT_DEDUP_SIMILARITY = 0.85  # similitud semántica para considerar duplicado
ALERT_MAX_PER_HOUR = 20        # anti-spam

# ---------------------------------------------------------------------------
# FastAPI
# ---------------------------------------------------------------------------
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))

# ---------------------------------------------------------------------------
# Scheduler – Ingesta automática
# ---------------------------------------------------------------------------
SCHEDULER_ENABLED = os.getenv("SCHEDULER_ENABLED", "true").lower() in ("true", "1", "yes")
SCHEDULER_INGEST_INTERVAL_MIN = int(os.getenv("SCHEDULER_INGEST_INTERVAL_MIN", "15"))
SCHEDULER_ALERTS_INTERVAL_MIN = int(os.getenv("SCHEDULER_ALERTS_INTERVAL_MIN", "20"))
SCHEDULER_BATCH_SIZE = int(os.getenv("SCHEDULER_BATCH_SIZE", "50"))
SCHEDULER_NEWS_RETENTION_DAYS = int(os.getenv("SCHEDULER_NEWS_RETENTION_DAYS", "30"))

# ---------------------------------------------------------------------------
# Notificaciones – Email + Webhook
# ---------------------------------------------------------------------------
NOTIFICATIONS_ENABLED = os.getenv("NOTIFICATIONS_ENABLED", "true").lower() in ("true", "1", "yes")

# SMTP (email)
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() in ("true", "1", "yes")
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "")
NOTIFICATION_EMAIL_TO = os.getenv("NOTIFICATION_EMAIL_TO", "")

# Webhook (Slack, Discord, Telegram bot, custom)
NOTIFICATION_WEBHOOK_URL = os.getenv("NOTIFICATION_WEBHOOK_URL", "")

# ---------------------------------------------------------------------------
# Streamlit
# ---------------------------------------------------------------------------
STREAMLIT_PORT = int(os.getenv("STREAMLIT_PORT", "8501"))

# ---------------------------------------------------------------------------
# Cloud Mode – Usa LLM en vez de modelos ML locales (ahorra ~2GB RAM)
# ---------------------------------------------------------------------------
CLOUD_MODE = os.getenv("CLOUD_MODE", "false").lower() in ("true", "1", "yes")

# Token secreto para proteger el endpoint /api/trigger-pipeline
CRON_SECRET = os.getenv("CRON_SECRET", "")

# Ruta del calibrador de severidad empírico (regresión isotónica score→|CAR|).
# Se ajusta con AlertBacktestService.fit_calibrator y lo carga el estimador.
SEVERITY_CALIBRATOR_PATH = os.getenv(
    "SEVERITY_CALIBRATOR_PATH",
    str(BASE_DIR / "data" / "severity_calibrator.json"),
)

# ---------------------------------------------------------------------------
# Capa de producción: seguridad, CORS, autenticación, observabilidad
# ---------------------------------------------------------------------------
# CORS: lista de orígenes permitidos separados por comas. "*" permite todos
# (solo recomendable en desarrollo). En producción, fijar el dominio del front.
CORS_ORIGINS = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", "*").split(",")
    if o.strip()
]

# Autenticación JWT. AUTH_ENABLED=false mantiene la API abierta (compatibilidad
# y desarrollo); =true exige token Bearer en los endpoints protegidos.
AUTH_ENABLED = os.getenv("AUTH_ENABLED", "false").lower() in ("true", "1", "yes")
JWT_SECRET = os.getenv("JWT_SECRET", "dev-insecure-secret-change-me")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))  # 24 h

# Rate limiting (slowapi). Formato slowapi: "N/period" (p.ej. "100/minute").
RATE_LIMIT_DEFAULT = os.getenv("RATE_LIMIT_DEFAULT", "120/minute")
RATE_LIMIT_AUTH = os.getenv("RATE_LIMIT_AUTH", "10/minute")
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() in ("true", "1", "yes")

# Logging estructurado JSON (recomendado en producción para agregadores).
LOG_JSON = os.getenv("LOG_JSON", "false").lower() in ("true", "1", "yes")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# Métricas Prometheus en /metrics.
METRICS_ENABLED = os.getenv("METRICS_ENABLED", "true").lower() in ("true", "1", "yes")

# Coste estimado del LLM por 1K tokens (USD), para el tracking de coste.
LLM_COST_PER_1K_PROMPT = float(os.getenv("LLM_COST_PER_1K_PROMPT", "0.0"))
LLM_COST_PER_1K_COMPLETION = float(os.getenv("LLM_COST_PER_1K_COMPLETION", "0.0"))

