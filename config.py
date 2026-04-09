"""
Configuración central del sistema de alertas inteligentes para carteras de inversión.
"""

import os
from pathlib import Path

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
# LLM (OpenAI / Azure OpenAI) – para clasificación compleja
# ---------------------------------------------------------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

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
ALERT_RELEVANCE_THRESHOLD = 0.5
ALERT_SEVERITY_THRESHOLD = 0.3
ALERT_DEDUP_SIMILARITY = 0.85  # similitud semántica para considerar duplicado
ALERT_MAX_PER_HOUR = 20        # anti-spam

# ---------------------------------------------------------------------------
# FastAPI
# ---------------------------------------------------------------------------
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))

# ---------------------------------------------------------------------------
# Streamlit
# ---------------------------------------------------------------------------
STREAMLIT_PORT = int(os.getenv("STREAMLIT_PORT", "8501"))
