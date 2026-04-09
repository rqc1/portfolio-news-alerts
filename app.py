"""
Frontend – InvestAlert Dashboard.
Professional dark-theme financial intelligence dashboard.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import streamlit as st
import streamlit_antd_components as sac
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

API_BASE = "http://localhost:8000"

# ═══════════════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ═══════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="InvestAlert — Inteligencia Financiera",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ═══════════════════════════════════════════════════════════════════════════
# CUSTOM CSS — Targets Streamlit's ACTUAL rendered DOM
# ═══════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
/* === FONTS === */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600&display=swap');

html, body, [class*="css"], .stMarkdown, .stText, p, span, label, h1, h2, h3, h4 {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
}

/* === MAIN CONTAINER === */
.main .block-container {
    padding: 1.5rem 2.5rem 4rem !important;
    max-width: 1440px !important;
}

/* === SIDEBAR === */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0a0e1a 0%, #111827 40%, #0f172a 100%) !important;
    border-right: 1px solid rgba(99,102,241,0.15) !important;
}
section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
    padding-top: 0 !important;
}

/* === METRIC CONTAINERS === */
[data-testid="stMetric"] {
    background: linear-gradient(145deg, #1a1c2e 0%, #1f2240 100%);
    border: 1px solid rgba(99,102,241,0.15);
    border-radius: 16px;
    padding: 20px 24px;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
[data-testid="stMetric"]:hover {
    border-color: rgba(99,102,241,0.4);
    box-shadow: 0 0 30px rgba(99,102,241,0.08);
    transform: translateY(-2px);
}
[data-testid="stMetric"] [data-testid="stMetricLabel"] {
    font-size: 0.72rem !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
    color: #8b92ab !important;
}
[data-testid="stMetric"] [data-testid="stMetricValue"] {
    font-size: 2.2rem !important;
    font-weight: 800 !important;
    letter-spacing: -0.03em !important;
    background: linear-gradient(135deg, #e2e8f0, #ffffff) !important;
    -webkit-background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
}
[data-testid="stMetric"] [data-testid="stMetricDelta"] {
    font-weight: 600 !important;
}

/* === TABS === */
.stTabs [data-baseweb="tab-list"] {
    background: #1a1c2e;
    border-radius: 14px;
    padding: 5px;
    gap: 4px;
    border: 1px solid rgba(99,102,241,0.1);
}
.stTabs [data-baseweb="tab"] {
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: 0.88rem !important;
    color: #8b92ab !important;
    padding: 10px 22px !important;
    transition: all 0.2s ease !important;
}
.stTabs [data-baseweb="tab"]:hover {
    color: #e2e8f0 !important;
    background: rgba(99,102,241,0.08) !important;
}
.stTabs [aria-selected="true"] {
    background: rgba(99,102,241,0.15) !important;
    color: #a5b4fc !important;
}
.stTabs [data-baseweb="tab-panel"] {
    padding-top: 24px !important;
}

/* === BUTTONS === */
.stButton > button {
    border-radius: 12px !important;
    font-weight: 700 !important;
    font-size: 0.88rem !important;
    padding: 10px 24px !important;
    border: 1px solid rgba(99,102,241,0.2) !important;
    background: linear-gradient(145deg, #1a1c2e, #1f2240) !important;
    color: #c4b5fd !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    letter-spacing: 0.01em !important;
}
.stButton > button:hover {
    background: linear-gradient(145deg, #6366f1, #7c3aed) !important;
    color: #ffffff !important;
    border-color: #6366f1 !important;
    box-shadow: 0 4px 20px rgba(99,102,241,0.3) !important;
    transform: translateY(-1px) !important;
}
.stButton > button[kind="primary"],
div[data-testid="stForm"] .stButton > button {
    background: linear-gradient(135deg, #6366f1 0%, #7c3aed 100%) !important;
    color: #ffffff !important;
    border: none !important;
    box-shadow: 0 4px 15px rgba(99,102,241,0.25) !important;
}
.stButton > button[kind="primary"]:hover,
div[data-testid="stForm"] .stButton > button:hover {
    background: linear-gradient(135deg, #7c3aed 0%, #9333ea 100%) !important;
    box-shadow: 0 6px 25px rgba(99,102,241,0.4) !important;
}

/* === INPUTS === */
.stTextInput input, .stTextArea textarea, .stNumberInput input {
    background: #1a1c2e !important;
    border: 1px solid rgba(99,102,241,0.15) !important;
    border-radius: 12px !important;
    color: #e2e8f0 !important;
    font-family: 'Inter', sans-serif !important;
    padding: 12px 16px !important;
}
.stTextInput input:focus, .stTextArea textarea:focus, .stNumberInput input:focus {
    border-color: #6366f1 !important;
    box-shadow: 0 0 0 3px rgba(99,102,241,0.15) !important;
}
.stTextInput label, .stTextArea label, .stNumberInput label, .stSelectbox label {
    font-weight: 600 !important;
    font-size: 0.82rem !important;
    color: #8b92ab !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
}

/* === SELECTBOX === */
.stSelectbox > div > div {
    background: #1a1c2e !important;
    border: 1px solid rgba(99,102,241,0.15) !important;
    border-radius: 12px !important;
}

/* === SLIDER === */
.stSlider [data-baseweb="slider"] [role="slider"] {
    background: #6366f1 !important;
}

/* === DATAFRAME === */
.stDataFrame {
    border: 1px solid rgba(99,102,241,0.12) !important;
    border-radius: 14px !important;
    overflow: hidden !important;
}

/* === EXPANDER === */
.streamlit-expanderHeader {
    background: #1a1c2e !important;
    border: 1px solid rgba(99,102,241,0.1) !important;
    border-radius: 12px !important;
    font-weight: 600 !important;
}

/* === DIVIDERS === */
hr {
    border-color: rgba(99,102,241,0.1) !important;
}

/* === CUSTOM SCROLLBAR === */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #0f1117; }
::-webkit-scrollbar-thumb { background: #2a2d45; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #3a3d58; }

/* === HIDE DEFAULTS === */
footer { visibility: hidden; }
#MainMenu { visibility: hidden; }
header[data-testid="stHeader"] { background: transparent !important; }

/* === ALERTS / SUCCESS / WARNING === */
.stAlert {
    border-radius: 12px !important;
    border: none !important;
}

/* === PLOTLY CHART CONTAINERS === */
.stPlotlyChart {
    background: #1a1c2e;
    border: 1px solid rgba(99,102,241,0.1);
    border-radius: 16px;
    padding: 16px;
}

/* === SPINNER === */
.stSpinner > div > div { border-top-color: #6366f1 !important; }

/* === FORM === */
[data-testid="stForm"] {
    background: #1a1c2e !important;
    border: 1px solid rgba(99,102,241,0.12) !important;
    border-radius: 16px !important;
    padding: 28px !important;
}

/* === CUSTOM COMPONENTS === */
.glass-card {
    background: linear-gradient(145deg, rgba(26,28,46,0.95), rgba(31,34,64,0.95));
    backdrop-filter: blur(20px);
    border: 1px solid rgba(99,102,241,0.12);
    border-radius: 20px;
    padding: 28px 32px;
    margin-bottom: 20px;
    transition: all 0.3s cubic-bezier(0.4,0,0.2,1);
}
.glass-card:hover {
    border-color: rgba(99,102,241,0.3);
    box-shadow: 0 8px 40px rgba(99,102,241,0.06);
}

.hero-banner {
    background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #172554 100%);
    border: 1px solid rgba(99,102,241,0.2);
    border-radius: 24px;
    padding: 44px 48px;
    margin-bottom: 32px;
    position: relative;
    overflow: hidden;
}
.hero-banner::before {
    content: '';
    position: absolute;
    top: -100px; right: -60px;
    width: 350px; height: 350px;
    background: radial-gradient(circle, rgba(99,102,241,0.12) 0%, transparent 70%);
    border-radius: 50%;
}
.hero-banner::after {
    content: '';
    position: absolute;
    bottom: -80px; left: 30%;
    width: 250px; height: 250px;
    background: radial-gradient(circle, rgba(6,182,212,0.08) 0%, transparent 70%);
    border-radius: 50%;
}
.hero-title {
    font-size: 2.2rem;
    font-weight: 900;
    background: linear-gradient(135deg, #ffffff 0%, #c4b5fd 50%, #a5b4fc 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin: 0 0 8px;
    letter-spacing: -0.04em;
    position: relative;
    z-index: 1;
    line-height: 1.1;
}
.hero-sub {
    font-size: 0.95rem;
    color: rgba(165,180,252,0.6);
    font-weight: 400;
    position: relative;
    z-index: 1;
    letter-spacing: 0.01em;
}

.section-label {
    display: inline-flex;
    align-items: center;
    gap: 10px;
    font-size: 0.72rem;
    font-weight: 800;
    color: #6366f1;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 6px;
}
.section-heading {
    font-size: 1.3rem;
    font-weight: 800;
    color: #e2e8f0;
    letter-spacing: -0.02em;
    margin-bottom: 20px;
}

.alert-card {
    background: linear-gradient(145deg, #1a1c2e, #1f2240);
    border: 1px solid rgba(99,102,241,0.1);
    border-left: 4px solid #64748b;
    border-radius: 16px;
    padding: 24px 28px;
    margin-bottom: 16px;
    transition: all 0.3s cubic-bezier(0.4,0,0.2,1);
}
.alert-card:hover {
    border-color: rgba(99,102,241,0.25);
    box-shadow: 0 8px 40px rgba(0,0,0,0.15);
    transform: translateY(-2px);
}
.alert-card.bajista { border-left-color: #ef4444; }
.alert-card.alcista { border-left-color: #10b981; }
.alert-card.neutral { border-left-color: #f59e0b; }

.alert-top { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 14px; }
.alert-title { font-weight: 700; font-size: 1rem; color: #e2e8f0; line-height: 1.4; flex: 1; }
.alert-time { font-size: 0.72rem; color: #4b5563; white-space: nowrap; padding-left: 16px; font-weight: 500; }

.badge-row { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 16px; }
.badge {
    display: inline-flex; align-items: center; gap: 5px;
    font-size: 0.68rem; font-weight: 700; padding: 5px 12px;
    border-radius: 8px; text-transform: uppercase; letter-spacing: 0.05em;
}
.badge-bajista { background: rgba(239,68,68,0.12); color: #f87171; border: 1px solid rgba(239,68,68,0.2); }
.badge-alcista { background: rgba(16,185,129,0.12); color: #34d399; border: 1px solid rgba(16,185,129,0.2); }
.badge-neutral { background: rgba(245,158,11,0.12); color: #fbbf24; border: 1px solid rgba(245,158,11,0.2); }
.badge-event { background: rgba(139,92,246,0.12); color: #a78bfa; border: 1px solid rgba(139,92,246,0.2); }
.badge-source { background: rgba(6,182,212,0.12); color: #22d3ee; border: 1px solid rgba(6,182,212,0.2); }

.sev-row { display: flex; align-items: center; gap: 16px; margin-bottom: 14px; }
.sev-block { text-align: center; }
.sev-val { font-size: 1.3rem; font-weight: 800; color: #e2e8f0; }
.sev-lbl { font-size: 0.62rem; font-weight: 700; color: #4b5563; text-transform: uppercase; letter-spacing: 0.06em; }
.sev-bar-outer { flex: 1; height: 8px; background: #1f2937; border-radius: 4px; overflow: hidden; }
.sev-bar-inner { height: 100%; border-radius: 4px; transition: width 0.6s ease; }
.sev-bar-inner.low { background: linear-gradient(90deg, #10b981, #34d399); }
.sev-bar-inner.med { background: linear-gradient(90deg, #f59e0b, #fbbf24); }
.sev-bar-inner.high { background: linear-gradient(90deg, #ef4444, #f87171); }

.alert-explain {
    font-size: 0.85rem; color: #9ca3af; line-height: 1.65;
    padding: 16px 20px;
    background: rgba(15,17,23,0.5);
    border-radius: 12px; margin-top: 14px;
    border-left: 3px solid rgba(99,102,241,0.2);
}

.alert-foot {
    display: flex; justify-content: space-between; align-items: center;
    margin-top: 14px; padding-top: 14px;
    border-top: 1px solid rgba(99,102,241,0.08);
}
.alert-assets { font-size: 0.8rem; color: #6b7280; }
.alert-assets strong { color: #9ca3af; }
.alert-link {
    font-size: 0.8rem; color: #818cf8; text-decoration: none;
    font-weight: 600; transition: color 0.2s;
}
.alert-link:hover { color: #a5b4fc; }

.news-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
    gap: 18px;
}
.news-item {
    background: linear-gradient(145deg, #1a1c2e, #1f2240);
    border: 1px solid rgba(99,102,241,0.08);
    border-radius: 18px;
    padding: 24px 26px;
    display: flex; flex-direction: column; gap: 12px;
    transition: all 0.3s cubic-bezier(0.4,0,0.2,1);
    position: relative; overflow: hidden;
}
.news-item:hover {
    border-color: rgba(99,102,241,0.3);
    box-shadow: 0 8px 40px rgba(99,102,241,0.06);
    transform: translateY(-3px);
}
.news-item::after {
    content: ''; position: absolute; top: 0; left: 0;
    width: 100%; height: 3px;
    background: linear-gradient(90deg, #6366f1, #a78bfa, #06b6d4);
    opacity: 0; transition: opacity 0.3s;
}
.news-item:hover::after { opacity: 1; }

.news-src { font-size: 0.68rem; font-weight: 700; color: #818cf8; text-transform: uppercase; letter-spacing: 0.06em; }
.news-title { font-weight: 700; font-size: 0.95rem; color: #e2e8f0; line-height: 1.45;
    display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }
.news-summary { font-size: 0.84rem; color: #6b7280; line-height: 1.55;
    display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.news-foot { display: flex; justify-content: space-between; align-items: center; margin-top: auto;
    padding-top: 12px; border-top: 1px solid rgba(99,102,241,0.08); }
.news-time { font-size: 0.7rem; color: #4b5563; font-weight: 500; }
.news-link { font-size: 0.78rem; color: #818cf8; text-decoration: none; font-weight: 600; }
.news-link:hover { color: #a5b4fc; }

.pipeline-grid {
    display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px;
    padding: 28px 32px;
    background: linear-gradient(135deg, #1e1b4b 0%, #172554 100%);
    border: 1px solid rgba(99,102,241,0.2);
    border-radius: 20px; margin: 16px 0;
}
.pipeline-cell { text-align: center; }
.pipeline-val { font-size: 2.4rem; font-weight: 900; color: #ffffff; line-height: 1; letter-spacing: -0.04em; }
.pipeline-lbl { font-size: 0.65rem; font-weight: 700; color: rgba(165,180,252,0.5);
    text-transform: uppercase; letter-spacing: 0.08em; margin-top: 6px; }

.source-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 16px; }
.source-card {
    background: linear-gradient(145deg, #1a1c2e, #1f2240);
    border: 1px solid rgba(99,102,241,0.1);
    border-radius: 16px; padding: 24px; text-align: center;
    transition: all 0.3s ease;
}
.source-card:hover { border-color: rgba(99,102,241,0.3); box-shadow: 0 4px 20px rgba(99,102,241,0.08); }
.source-icon { font-size: 2.2rem; margin-bottom: 12px; }
.source-name { font-weight: 700; font-size: 0.92rem; color: #e2e8f0; margin-bottom: 4px; }
.source-desc { font-size: 0.75rem; color: #6b7280; line-height: 1.4; }

.config-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 14px; }
.config-item {
    background: linear-gradient(145deg, #1a1c2e, #1f2240);
    border: 1px solid rgba(99,102,241,0.1);
    border-radius: 14px; padding: 20px 22px;
    display: flex; align-items: center; gap: 16px;
}
.config-icon {
    width: 44px; height: 44px; border-radius: 12px;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.2rem; background: rgba(99,102,241,0.1); flex-shrink: 0;
}
.config-label { font-size: 0.7rem; font-weight: 700; color: #6b7280;
    text-transform: uppercase; letter-spacing: 0.05em; }
.config-value { font-size: 0.88rem; font-weight: 600; color: #e2e8f0;
    font-family: 'JetBrains Mono', monospace; }

.empty-box {
    text-align: center; padding: 60px 40px;
    background: linear-gradient(145deg, #1a1c2e, #1f2240);
    border: 2px dashed rgba(99,102,241,0.15);
    border-radius: 24px; margin: 24px 0;
}
.empty-icon { font-size: 3rem; margin-bottom: 16px; opacity: 0.4; }
.empty-title { font-size: 1.1rem; font-weight: 700; color: #e2e8f0; margin-bottom: 8px; }
.empty-text { font-size: 0.88rem; color: #6b7280; max-width: 400px; margin: 0 auto; line-height: 1.5; }

.portfolio-card {
    background: linear-gradient(145deg, #1a1c2e, #1f2240);
    border: 1px solid rgba(99,102,241,0.1);
    border-radius: 20px; padding: 32px; margin-bottom: 24px;
    transition: all 0.3s ease;
}
.portfolio-card:hover { border-color: rgba(99,102,241,0.25); }
.portfolio-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.portfolio-name { font-size: 1.35rem; font-weight: 800; color: #e2e8f0; letter-spacing: -0.02em; }
.portfolio-id { font-family: 'JetBrains Mono', monospace; font-size: 0.68rem; color: #6b7280;
    background: rgba(99,102,241,0.08); padding: 5px 12px; border-radius: 8px; }

.status-pill {
    display: inline-flex; align-items: center; gap: 8px;
    font-size: 0.78rem; font-weight: 600; color: #9ca3af;
}
.status-pill .dot {
    width: 8px; height: 8px; border-radius: 50%; display: inline-block;
}
.status-pill .dot.on { background: #10b981; box-shadow: 0 0 8px rgba(16,185,129,0.5); }
.status-pill .dot.off { background: #ef4444; box-shadow: 0 0 8px rgba(239,68,68,0.5); }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# SESSION STATE
# ═══════════════════════════════════════════════════════════════════════════
for k, v in [("portfolio_id", ""), ("user_id", "default_user"), ("selected_portfolio_name", "")]:
    if k not in st.session_state:
        st.session_state[k] = v


# ═══════════════════════════════════════════════════════════════════════════
# API HELPERS
# ═══════════════════════════════════════════════════════════════════════════
def api_get(endpoint: str, params: dict | None = None):
    try:
        r = requests.get(f"{API_BASE}{endpoint}", params=params, timeout=30)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        st.error("⛔ No se puede conectar con el backend (puerto 8000).")
        return None
    except Exception as e:
        st.error(f"Error API: {e}")
        return None


def api_post(endpoint: str, json_data: dict | None = None, params: dict | None = None):
    try:
        r = requests.post(f"{API_BASE}{endpoint}", json=json_data, params=params, timeout=120)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        st.error("⛔ No se puede conectar con el backend.")
        return None
    except Exception as e:
        st.error(f"Error API: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════════════
# PLOTLY THEME
# ═══════════════════════════════════════════════════════════════════════════
PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter", size=12, color="#8b92ab"),
    margin=dict(l=0, r=0, t=10, b=0),
    xaxis=dict(showgrid=True, gridcolor="rgba(99,102,241,0.06)", zeroline=False),
    yaxis=dict(showgrid=True, gridcolor="rgba(99,102,241,0.06)", zeroline=False),
    legend=dict(font=dict(size=12, color="#9ca3af"), orientation="h", y=-0.15, x=0.5, xanchor="center"),
)
COLOR_SEQ = ["#6366f1", "#a78bfa", "#06b6d4", "#10b981", "#f59e0b", "#ef4444", "#ec4899", "#8b5cf6"]


# ═══════════════════════════════════════════════════════════════════════════
# REUSABLE COMPONENTS
# ═══════════════════════════════════════════════════════════════════════════
def hero(title: str, subtitle: str):
    st.markdown(f"""
    <div class="hero-banner">
        <div class="hero-title">{title}</div>
        <div class="hero-sub">{subtitle}</div>
    </div>
    """, unsafe_allow_html=True)


def section(label: str, heading: str):
    st.markdown(f"""
    <div class="section-label">● {label}</div>
    <div class="section-heading">{heading}</div>
    """, unsafe_allow_html=True)


def render_alert(a: dict):
    direction = a.get("direction", "neutral")
    event = a.get("event_type", "otro").replace("_", " ").title()
    source = a.get("news_source", "")
    severity = a.get("severity", 0)
    confidence = a.get("confidence", 0)
    assets = ", ".join(a.get("matched_assets", []))
    title = a.get("news_title", "Sin título")
    explanation = a.get("explanation", "")
    url = a.get("news_url", "")
    created = a.get("created_at", "")
    if created:
        try:
            created = datetime.fromisoformat(created).strftime("%d %b %Y · %H:%M")
        except Exception:
            pass

    dc = direction if direction in ("bajista", "alcista", "neutral") else "neutral"
    sw = f"{severity * 100:.0f}%"
    sl = "low" if severity < 0.35 else ("med" if severity < 0.65 else "high")
    link = f'<a class="alert-link" href="{url}" target="_blank" rel="noopener">Ver fuente →</a>' if url else ""

    st.markdown(f"""
    <div class="alert-card {dc}">
        <div class="alert-top">
            <div class="alert-title">{title}</div>
            <div class="alert-time">{created}</div>
        </div>
        <div class="badge-row">
            <span class="badge badge-{dc}">● {direction.upper()}</span>
            <span class="badge badge-event">{event}</span>
            {"<span class='badge badge-source'>" + source + "</span>" if source else ""}
        </div>
        <div class="sev-row">
            <div class="sev-block"><div class="sev-val">{severity:.0%}</div><div class="sev-lbl">Severidad</div></div>
            <div class="sev-bar-outer"><div class="sev-bar-inner {sl}" style="width:{sw}"></div></div>
            <div class="sev-block"><div class="sev-val">{confidence:.0%}</div><div class="sev-lbl">Confianza</div></div>
        </div>
        {"<div class='alert-explain'>" + explanation + "</div>" if explanation else ""}
        <div class="alert-foot">
            <div class="alert-assets"><strong>Activos:</strong> {assets}</div>
            {link}
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_news(items: list):
    html = ""
    for it in items:
        title = it.get("title", "Sin título")
        src = it.get("source", "")
        stype = it.get("source_type", "")
        pub = it.get("published_at", "")
        lang = it.get("language", "")
        summary = (it.get("summary") or "")[:220]
        url = it.get("url", "")
        if pub:
            try:
                pub = datetime.fromisoformat(pub).strftime("%d %b %Y · %H:%M")
            except Exception:
                pass
        link = f'<a class="news-link" href="{url}" target="_blank" rel="noopener">Leer →</a>' if url else ""
        html += f"""
        <div class="news-item">
            <div class="news-src">● {src} · {stype}{(" · " + lang.upper()) if lang else ""}</div>
            <div class="news-title">{title}</div>
            {"<div class='news-summary'>" + summary + "</div>" if summary else ""}
            <div class="news-foot"><span class="news-time">{pub}</span>{link}</div>
        </div>"""
    st.markdown(f'<div class="news-grid">{html}</div>', unsafe_allow_html=True)


def empty(icon: str, title: str, text: str):
    st.markdown(f"""
    <div class="empty-box">
        <div class="empty-icon">{icon}</div>
        <div class="empty-title">{title}</div>
        <div class="empty-text">{text}</div>
    </div>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# SIDEBAR — Professional dark navigation
# ═══════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("""
    <div style="padding:16px 0 10px;">
        <div style="display:flex;align-items:center;gap:12px;">
            <div style="width:40px;height:40px;background:linear-gradient(135deg,#6366f1,#a78bfa);border-radius:12px;display:flex;align-items:center;justify-content:center;box-shadow:0 4px 15px rgba(99,102,241,0.3);">
                <span style="font-size:1.15rem;">⚡</span>
            </div>
            <div>
                <div style="font-size:1.2rem;font-weight:900;color:#e2e8f0;letter-spacing:-0.04em;">InvestAlert</div>
                <div style="font-size:0.6rem;font-weight:700;color:#4b5563;letter-spacing:0.1em;text-transform:uppercase;">Inteligencia Financiera</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    page_idx = sac.menu([
        sac.MenuItem("Dashboard", icon="speedometer2"),
        sac.MenuItem("Cartera", icon="briefcase"),
        sac.MenuItem("Noticias", icon="newspaper"),
        sac.MenuItem("Motor de Alertas", icon="lightning-charge"),
        sac.MenuItem("Configuración", icon="gear"),
    ], open_all=False, indent=20, size="md")

    st.markdown("---")

    # Portfolio selector
    st.markdown('<div style="font-size:0.62rem;font-weight:800;color:#4b5563;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:4px;">Cartera activa</div>', unsafe_allow_html=True)
    portfolios_sidebar = api_get("/api/portfolios", params={"user_id": st.session_state.user_id})
    if portfolios_sidebar:
        pnames = {p.get("_id", ""): p.get("name", "Sin nombre") for p in portfolios_sidebar}
        opts = list(pnames.keys())
        if st.session_state.portfolio_id in opts:
            didx = opts.index(st.session_state.portfolio_id)
        elif opts:
            didx = 0
        else:
            didx = 0
        if opts:
            sel = st.selectbox("Cartera", opts, index=didx, format_func=lambda x: pnames.get(x, x), label_visibility="collapsed")
            st.session_state.portfolio_id = sel
            st.session_state.selected_portfolio_name = pnames.get(sel, "")
    else:
        st.caption("Sin carteras")

    st.markdown("---")

    health = api_get("/health")
    if health:
        st.markdown('<div class="status-pill"><span class="dot on"></span>Backend conectado</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="status-pill"><span class="dot off"></span>Backend offline</div>', unsafe_allow_html=True)

    st.markdown('<div style="margin-top:32px;text-align:center;font-size:0.6rem;color:#374151;">InvestAlert v1.0 · TFM UNIR</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# PAGE ROUTING
# ═══════════════════════════════════════════════════════════════════════════
page = page_idx  # sac.menu returns the label string

# ═══════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════
if page == "Dashboard":
    pname = st.session_state.selected_portfolio_name or "Sin cartera seleccionada"
    hero("Panel de Control", f"Cartera activa: {pname} · Monitorización en tiempo real")

    pid = st.session_state.portfolio_id
    stats = api_get("/api/alerts/stats", params={"portfolio_id": pid} if pid else None)
    alerts_data = api_get("/api/alerts", params={"portfolio_id": pid, "limit": 200} if pid else {"limit": 200})

    total = stats.get("total", 0) if stats else 0
    avg_sev = stats.get("avg_severity", 0) if stats else 0
    avg_conf = stats.get("avg_confidence", 0) if stats else 0

    n_baj = n_alc = n_neu = 0
    if alerts_data:
        for a in alerts_data:
            d = a.get("direction", "")
            if d == "bajista": n_baj += 1
            elif d == "alcista": n_alc += 1
            else: n_neu += 1

    # KPI metrics row — using Streamlit native st.metric (which our CSS styles)
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Total Alertas", total)
    k2.metric("Bajistas", n_baj, delta=f"{n_baj/(total or 1):.0%} del total", delta_color="inverse")
    k3.metric("Alcistas", n_alc, delta=f"{n_alc/(total or 1):.0%} del total")
    k4.metric("Severidad Media", f"{avg_sev:.0%}" if avg_sev else "—")
    k5.metric("Confianza Media", f"{avg_conf:.0%}" if avg_conf else "—")

    st.markdown("<br>", unsafe_allow_html=True)

    # Charts
    if alerts_data:
        df = pd.DataFrame(alerts_data)

        col_l, col_r = st.columns(2)

        with col_l:
            section("ANÁLISIS", "Distribución por Evento")
            if "event_type" in df.columns:
                ec = df["event_type"].value_counts().reset_index()
                ec.columns = ["Tipo", "Cantidad"]
                fig = px.bar(ec, x="Cantidad", y="Tipo", orientation="h",
                             color="Cantidad", color_continuous_scale=["#312e81", "#6366f1", "#a78bfa"])
                fig.update_layout(**{**PLOTLY_LAYOUT, "yaxis": dict(autorange="reversed", showgrid=False, gridcolor="rgba(99,102,241,0.06)")},
                                  height=340, showlegend=False, coloraxis_showscale=False)
                fig.update_traces(marker_line_width=0, marker_cornerradius=6)
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        with col_r:
            section("DIRECCIÓN", "Impacto en Cartera")
            if "direction" in df.columns:
                dc = df["direction"].value_counts().reset_index()
                dc.columns = ["Dirección", "Cantidad"]
                cmap = {"bajista": "#ef4444", "alcista": "#10b981", "neutral": "#f59e0b"}
                fig2 = px.pie(dc, values="Cantidad", names="Dirección", color="Dirección",
                              color_discrete_map=cmap, hole=0.65)
                fig2.update_layout(**PLOTLY_LAYOUT, height=340)
                fig2.update_traces(textinfo="percent+value", textfont=dict(size=14, color="#e2e8f0"),
                                   marker=dict(line=dict(color="#0f1117", width=3)))
                st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

        # Scatter
        if "severity" in df.columns and "confidence" in df.columns:
            section("CORRELACIÓN", "Severidad vs. Confianza")
            cmap_s = {"bajista": "#ef4444", "alcista": "#10b981", "neutral": "#f59e0b"}
            fig3 = px.scatter(df, x="severity", y="confidence",
                              color="direction" if "direction" in df.columns else None,
                              color_discrete_map=cmap_s, size_max=14,
                              labels={"severity": "Severidad", "confidence": "Confianza", "direction": "Dirección"},
                              hover_data=["news_title"] if "news_title" in df.columns else None)
            fig3.update_layout(**PLOTLY_LAYOUT, height=320,
                               xaxis=dict(range=[0, 1], showgrid=True, gridcolor="rgba(99,102,241,0.06)"),
                               yaxis=dict(range=[0, 1], showgrid=True, gridcolor="rgba(99,102,241,0.06)"))
            fig3.update_traces(marker=dict(size=11, line=dict(width=2, color="#0f1117")))
            st.plotly_chart(fig3, use_container_width=True, config={"displayModeBar": False})

    st.markdown("<br>", unsafe_allow_html=True)

    # Recent alerts
    section("ÚLTIMAS ALERTAS", "Actividad Reciente")
    recent = api_get("/api/alerts", params={"portfolio_id": pid, "limit": 6} if pid else {"limit": 6})
    if recent:
        for al in recent:
            render_alert(al)
    else:
        empty("🔔", "Sin alertas todavía", "Ingesta noticias y procésalas desde el Motor de Alertas.")


# ═══════════════════════════════════════════════════════════════════════════
# CARTERA
# ═══════════════════════════════════════════════════════════════════════════
elif page == "Cartera":
    hero("Gestión de Cartera", "Administra activos, pesos y composición sectorial")

    tab_view, tab_create, tab_add = st.tabs(["📋  Mis Carteras", "➕  Nueva Cartera", "🔗  Añadir Activo"])

    with tab_view:
        portfolios = api_get("/api/portfolios", params={"user_id": st.session_state.user_id})
        if portfolios:
            for p in portfolios:
                pn = p.get("name", "Sin nombre")
                pid_v = p.get("_id", "")
                assets = p.get("assets", [])

                st.markdown(f"""
                <div class="portfolio-card">
                    <div class="portfolio-head">
                        <div class="portfolio-name">{pn}</div>
                        <div class="portfolio-id">{pid_v}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                if assets:
                    df = pd.DataFrame(assets)
                    dcols = [c for c in ["ticker", "name", "sector", "country", "weight"] if c in df.columns]
                    dfd = df[dcols].copy()
                    if "weight" in dfd.columns:
                        dfd["weight"] = dfd["weight"].apply(lambda x: f"{x:.0%}")
                        dfd = dfd.rename(columns={"weight": "Peso", "ticker": "Ticker", "name": "Nombre", "sector": "Sector", "country": "País"})
                    st.dataframe(dfd, use_container_width=True, hide_index=True)

                    c_pie, c_bar = st.columns(2)
                    with c_pie:
                        if "weight" in df.columns and len(df) > 1:
                            fig = px.pie(df, values="weight", names="ticker",
                                         color_discrete_sequence=COLOR_SEQ, hole=0.55)
                            fig.update_layout(**PLOTLY_LAYOUT, height=300,
                                              title=dict(text="Distribución por activo", font=dict(size=14, color="#e2e8f0")))
                            fig.update_traces(textinfo="label+percent", textfont=dict(size=11, color="#9ca3af"),
                                              marker=dict(line=dict(color="#0f1117", width=2)))
                            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

                    with c_bar:
                        if "sector" in df.columns and "weight" in df.columns:
                            sw = df.groupby("sector")["weight"].sum().reset_index()
                            sw.columns = ["Sector", "Peso"]
                            fig2 = px.bar(sw, x="Sector", y="Peso", color_discrete_sequence=["#6366f1"])
                            fig2.update_layout(**PLOTLY_LAYOUT, height=300,
                                               title=dict(text="Peso por sector", font=dict(size=14, color="#e2e8f0")),
                                               yaxis=dict(tickformat=".0%", showgrid=True, gridcolor="rgba(99,102,241,0.06)"))
                            fig2.update_traces(marker_line_width=0, marker_cornerradius=8)
                            st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})
                else:
                    st.caption("Sin activos todavía.")
                st.markdown("<br>", unsafe_allow_html=True)
        else:
            empty("💼", "Sin carteras creadas", "Crea tu primera cartera en la pestaña Nueva Cartera.")

    with tab_create:
        section("NUEVA CARTERA", "Crear cartera de inversión")
        with st.form("create_portfolio", clear_on_submit=True):
            c1, c2 = st.columns(2)
            name = c1.text_input("Nombre", placeholder="Mi Cartera Tecnológica")
            uid = c2.text_input("User ID", value=st.session_state.user_id)
            if st.form_submit_button("✨ Crear Cartera", use_container_width=True):
                if name:
                    res = api_post("/api/portfolios", {"user_id": uid, "name": name})
                    if res:
                        st.session_state.portfolio_id = res.get("portfolio_id", "")
                        st.success(f"✅ Cartera «{name}» creada.")
                        st.rerun()

    with tab_add:
        section("AÑADIR ACTIVO", "Agregar activo a cartera activa")
        if not st.session_state.portfolio_id:
            empty("💼", "Sin cartera seleccionada", "Selecciona una cartera en la barra lateral.")
        else:
            sac.alert(f"Cartera activa: **{st.session_state.selected_portfolio_name}**",
                      banner=False, icon=True, closable=False, variant="filled", color="blue", size="md")
            with st.form("add_asset", clear_on_submit=True):
                c1, c2 = st.columns(2)
                ticker = c1.text_input("Ticker", placeholder="AAPL")
                name = c2.text_input("Nombre", placeholder="Apple Inc.")
                c3, c4, c5 = st.columns(3)
                sector = c3.text_input("Sector", placeholder="Technology")
                country = c4.text_input("País (ISO 2)", placeholder="US")
                weight = c5.number_input("Peso (0–1)", 0.0, 1.0, 0.10, 0.05)
                aliases = st.text_input("Aliases (coma)", placeholder="Apple, AAPL US Equity")
                if st.form_submit_button("➕ Añadir Activo", use_container_width=True):
                    if ticker:
                        alist = [a.strip() for a in aliases.split(",") if a.strip()]
                        res = api_post(f"/api/portfolios/{st.session_state.portfolio_id}/assets",
                                       {"ticker": ticker, "name": name, "sector": sector,
                                        "country": country, "weight": weight, "aliases": alist})
                        if res:
                            st.success(f"✅ {ticker} añadido.")
                            st.rerun()


# ═══════════════════════════════════════════════════════════════════════════
# NOTICIAS
# ═══════════════════════════════════════════════════════════════════════════
elif page == "Noticias":
    hero("Centro de Noticias", "Adquiere, explora y monitoriza noticias financieras globales")

    tab_ing, tab_br = st.tabs(["🔄  Ingestar Fuentes", "📋  Explorar Noticias"])

    with tab_ing:
        section("FUENTES PRIMARIAS", "Ingesta sin API key")

        cols = st.columns(3)
        with cols[0]:
            st.markdown("""
            <div class="source-card">
                <div class="source-icon">🌐</div>
                <div class="source-name">Todas las fuentes</div>
                <div class="source-desc">RSS + SEC EDGAR + CNMV · Ingesta completa</div>
            </div>""", unsafe_allow_html=True)
            if st.button("⚡ Ingestar todo", key="i_all", use_container_width=True):
                with st.spinner("Ingesta en progreso..."):
                    res = api_post("/api/ingest")
                if res: st.success(f"✅ {res.get('stats', res)}")

        with cols[1]:
            st.markdown("""
            <div class="source-card">
                <div class="source-icon">📡</div>
                <div class="source-name">RSS Feeds</div>
                <div class="source-desc">22 feeds · Finanzas, macro, cyber, supply chain</div>
            </div>""", unsafe_allow_html=True)
            if st.button("📡 Solo RSS", key="i_rss", use_container_width=True):
                with st.spinner("Descargando feeds RSS..."):
                    res = api_post("/api/ingest/rss")
                if res: st.success(f"✅ {res.get('count', 0)} noticias")

        with cols[2]:
            st.markdown("""
            <div class="source-card">
                <div class="source-icon">🇪🇸</div>
                <div class="source-name">CNMV</div>
                <div class="source-desc">Hechos relevantes · Información privilegiada</div>
            </div>""", unsafe_allow_html=True)
            if st.button("🇪🇸 Solo CNMV", key="i_cnmv", use_container_width=True):
                with st.spinner("Descargando CNMV..."):
                    res = api_post("/api/ingest/cnmv")
                if res: st.success(f"✅ {res.get('count', 0)} noticias")

        st.markdown("<br>", unsafe_allow_html=True)
        section("FUENTES ENRIQUECIDAS", "Requieren API key gratuita")

        c4, c5 = st.columns(2)
        with c4:
            st.markdown("""
            <div class="source-card">
                <div class="source-icon">🌍</div>
                <div class="source-name">NewsAPI.org</div>
                <div class="source-desc">+150k fuentes globales · Texto completo</div>
            </div>""", unsafe_allow_html=True)
            q = st.text_input("Buscar", placeholder="Apple earnings OR Tesla regulation", key="newsapi_q", label_visibility="collapsed")
            if st.button("🔍 Buscar NewsAPI", key="i_newsapi", use_container_width=True):
                if q:
                    with st.spinner("Buscando..."):
                        res = api_post("/api/ingest/newsapi", params={"query": q})
                    if res: st.success(f"✅ {res.get('count', 0)} noticias")
                else: st.warning("Introduce un término de búsqueda.")

        with c5:
            st.markdown("""
            <div class="source-card">
                <div class="source-icon">📈</div>
                <div class="source-name">Alpha Vantage</div>
                <div class="source-desc">Tickers anotados · Sentiment pre-calculado</div>
            </div>""", unsafe_allow_html=True)
            tks = st.text_input("Tickers", placeholder="AAPL,MSFT,TSLA", key="av_t", label_visibility="collapsed")
            if st.button("📈 Buscar Alpha Vantage", key="i_av", use_container_width=True):
                if tks:
                    with st.spinner("Buscando..."):
                        res = api_post("/api/ingest/alphavantage", params={"tickers": tks})
                    if res: st.success(f"✅ {res.get('count', 0)} noticias")
                else: st.warning("Introduce tickers separados por coma.")

    with tab_br:
        section("EXPLORAR", "Noticias almacenadas")
        lim = st.select_slider("Mostrar", [20, 50, 100, 200], value=50)
        news = api_get("/api/news", params={"limit": lim})
        if news:
            sac.alert(f"Mostrando **{len(news)}** noticias más recientes",
                      banner=False, icon=True, closable=False, variant="quote", size="sm")
            render_news(news)
        else:
            empty("📰", "Sin noticias", "Usa la pestaña Ingestar para adquirir noticias.")


# ═══════════════════════════════════════════════════════════════════════════
# MOTOR DE ALERTAS
# ═══════════════════════════════════════════════════════════════════════════
elif page == "Motor de Alertas":
    hero("Motor de Alertas NLP", "Pipeline: NLP → Relevancia → Clasificación → Impacto → Dedup → Alerta")

    tab_b, tab_m, tab_h = st.tabs(["🚀  Procesar Batch", "✍️  Análisis Manual", "📋  Historial"])

    with tab_b:
        pid = st.session_state.portfolio_id
        if not pid:
            empty("💼", "Sin cartera seleccionada", "Selecciona una cartera en la barra lateral.")
        else:
            section("PIPELINE NLP", f"Procesando para: {st.session_state.selected_portfolio_name}")
            sac.alert(
                "Cada noticia pasa por: preprocesamiento → entidades → relevancia → clasificación → impacto → dedup → alerta.",
                banner=False, icon=True, closable=False, variant="quote", size="sm"
            )

            c1, c2 = st.columns([3, 1])
            bl = c1.slider("Noticias a procesar", 10, 200, 50, step=10)
            with c2:
                st.markdown("<br>", unsafe_allow_html=True)
                run = st.button("▶  Ejecutar Pipeline", use_container_width=True, type="primary")

            if run:
                with st.spinner("Procesando pipeline NLP..."):
                    res = api_post(f"/api/alerts/process-batch/{pid}", params={"limit": bl})
                if res:
                    pr = res.get("processed", 0)
                    gen = res.get("alerts_generated", 0)
                    dup = res.get("duplicates", 0)
                    dis = res.get("discarded", 0)

                    st.markdown(f"""
                    <div class="pipeline-grid">
                        <div class="pipeline-cell"><div class="pipeline-val">{pr}</div><div class="pipeline-lbl">Procesadas</div></div>
                        <div class="pipeline-cell"><div class="pipeline-val">{gen}</div><div class="pipeline-lbl">Alertas</div></div>
                        <div class="pipeline-cell"><div class="pipeline-val">{dup}</div><div class="pipeline-lbl">Duplicados</div></div>
                        <div class="pipeline-cell"><div class="pipeline-val">{dis}</div><div class="pipeline-lbl">Descartadas</div></div>
                    </div>
                    """, unsafe_allow_html=True)

                    if gen > 0:
                        section("GENERADAS", "Alertas de este batch")
                        newa = api_get("/api/alerts", params={"portfolio_id": pid, "limit": gen})
                        if newa:
                            for a in newa:
                                render_alert(a)

    with tab_m:
        section("ANÁLISIS MANUAL", "Analizar noticia individual")
        sac.alert("Introduce una noticia para analizarla contra la cartera activa.",
                  banner=False, icon=True, closable=False, variant="quote", size="sm")

        with st.form("manual_news", clear_on_submit=False):
            title = st.text_input("Titular", placeholder="Apple reports lower than expected Q2 earnings amid China slowdown")
            summary = st.text_area("Cuerpo / Resumen", placeholder="Pega aquí el texto de la noticia...", height=120)
            c1, c2 = st.columns(2)
            source = c1.text_input("Fuente", value="manual")
            url = c2.text_input("URL (opcional)")
            if st.form_submit_button("🔍 Analizar Noticia", use_container_width=True):
                if title:
                    with st.spinner("Analizando..."):
                        res = api_post("/api/alerts/process", {
                            "title": title, "summary": summary, "content": "", "url": url,
                            "source": source, "portfolio_id": st.session_state.portfolio_id,
                        })
                    if res:
                        if res.get("status") == "alert_generated":
                            st.success("✅ Alerta generada")
                            render_alert(res["alert"])
                        else:
                            reason = res.get("reason", "No superó los umbrales.")
                            sac.alert(f"Sin alerta: {reason}", variant="warning", icon=True, closable=False)

    with tab_h:
        pid = st.session_state.portfolio_id
        section("HISTORIAL", "Todas las alertas generadas")
        alerts = api_get("/api/alerts", params={"portfolio_id": pid, "limit": 200} if pid else {"limit": 200})
        if alerts:
            df = pd.DataFrame(alerts)
            if not df.empty:
                cmap = {"news_title": "Titular", "event_type": "Evento", "direction": "Dirección",
                        "severity_label": "Severidad", "severity": "Score", "confidence": "Confianza",
                        "matched_assets": "Activos", "news_source": "Fuente"}
                av = {k: v for k, v in cmap.items() if k in df.columns}
                dfs = df[list(av.keys())].rename(columns=av)
                if "Score" in dfs.columns: dfs["Score"] = dfs["Score"].apply(lambda x: f"{x:.2f}")
                if "Confianza" in dfs.columns: dfs["Confianza"] = dfs["Confianza"].apply(lambda x: f"{x:.2f}")
                if "Activos" in dfs.columns: dfs["Activos"] = dfs["Activos"].apply(lambda x: ", ".join(x) if isinstance(x, list) else str(x))
                st.dataframe(dfs, use_container_width=True, hide_index=True, height=400)

            cL, cR = st.columns(2)
            with cL:
                if "event_type" in df.columns:
                    ec = df["event_type"].value_counts().reset_index()
                    ec.columns = ["Tipo", "Cantidad"]
                    fig = px.bar(ec, x="Cantidad", y="Tipo", orientation="h", color_discrete_sequence=["#6366f1"])
                    fig.update_layout(**{**PLOTLY_LAYOUT, "yaxis": dict(autorange="reversed", showgrid=False)}, height=300)
                    fig.update_traces(marker_line_width=0, marker_cornerradius=6)
                    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            with cR:
                if "severity" in df.columns:
                    fig4 = px.histogram(df, x="severity", nbins=20, color_discrete_sequence=["#a78bfa"],
                                        labels={"severity": "Severidad", "count": "Frecuencia"})
                    fig4.update_layout(**{**PLOTLY_LAYOUT, "xaxis": dict(range=[0, 1], showgrid=True, gridcolor="rgba(99,102,241,0.06)")}, height=300, bargap=0.08)
                    fig4.update_traces(marker_line_width=0, marker_cornerradius=4)
                    st.plotly_chart(fig4, use_container_width=True, config={"displayModeBar": False})
        else:
            empty("📋", "Sin historial", "Ejecuta el pipeline para generar alertas.")


# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════════════════════
elif page == "Configuración":
    hero("Configuración", "Modelos NLP, umbrales, fuentes y parámetros del pipeline")

    try:
        from config import (
            FINBERT_MODEL, SPACY_MODEL, EMBEDDING_MODEL,
            RELEVANCE_THRESHOLD, SEVERITY_THRESHOLD,
            DEDUP_SIMILARITY_THRESHOLD, MAX_ALERTS_PER_HOUR,
            NEWS_SOURCES, EVENT_TYPES,
        )

        section("MODELOS NLP", "Modelos de procesamiento configurados")
        st.markdown(f"""
        <div class="config-grid">
            <div class="config-item">
                <div class="config-icon">🤖</div>
                <div><div class="config-label">Sentiment (FinBERT)</div><div class="config-value">{FINBERT_MODEL}</div></div>
            </div>
            <div class="config-item">
                <div class="config-icon">🏷️</div>
                <div><div class="config-label">SpaCy NER</div><div class="config-value">{SPACY_MODEL}</div></div>
            </div>
            <div class="config-item">
                <div class="config-icon">🔗</div>
                <div><div class="config-label">Embeddings</div><div class="config-value">{EMBEDDING_MODEL}</div></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        section("UMBRALES", "Parámetros del pipeline de alertas")
        st.markdown(f"""
        <div class="config-grid">
            <div class="config-item">
                <div class="config-icon">🎯</div>
                <div><div class="config-label">Relevancia mínima</div><div class="config-value">{RELEVANCE_THRESHOLD}</div></div>
            </div>
            <div class="config-item">
                <div class="config-icon">⚠️</div>
                <div><div class="config-label">Severidad mínima</div><div class="config-value">{SEVERITY_THRESHOLD}</div></div>
            </div>
            <div class="config-item">
                <div class="config-icon">🔄</div>
                <div><div class="config-label">Similitud dedup.</div><div class="config-value">{DEDUP_SIMILARITY_THRESHOLD}</div></div>
            </div>
            <div class="config-item">
                <div class="config-icon">⏱️</div>
                <div><div class="config-label">Máx alertas/hora</div><div class="config-value">{MAX_ALERTS_PER_HOUR}</div></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        section("TAXONOMÍA", "Tipos de eventos detectados")
        try:
            from modules.events.classifier import EVENT_DESCRIPTIONS
            edata = [{"Tipo": et.replace("_", " ").title(), "Código": et, "Descripción": EVENT_DESCRIPTIONS.get(et, "")}
                     for et in EVENT_TYPES]
            if edata:
                st.dataframe(pd.DataFrame(edata), use_container_width=True, hide_index=True)
        except ImportError:
            for et in EVENT_TYPES:
                st.markdown(f"- `{et}`")

        st.markdown("<br>", unsafe_allow_html=True)
        section("FUENTES", "Fuentes de noticias configuradas")
        if NEWS_SOURCES:
            types = {}
            for s in NEWS_SOURCES:
                types.setdefault(s.get("type", "Otro"), []).append(s.get("name", ""))
            for tp, names in types.items():
                with st.expander(f"**{tp}** — {len(names)} fuentes"):
                    for n in names:
                        st.markdown(f"- {n}")

    except ImportError as e:
        st.error(f"Error importando configuración: {e}")
