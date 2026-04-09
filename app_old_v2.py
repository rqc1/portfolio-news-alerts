"""
Frontend – Streamlit Dashboard.

Interfaz web profesional para gestionar carteras, visualizar noticias y consultar alertas.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

API_BASE = "http://localhost:8000"

# ---------------------------------------------------------------------------
# Page config & custom CSS
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="InvestAlert · Alertas Inteligentes",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
/* ---- Global ---- */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

/* ---- Sidebar ---- */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
    color: #e2e8f0;
}
section[data-testid="stSidebar"] .stRadio label { color: #cbd5e1 !important; font-size: 0.95rem; }
section[data-testid="stSidebar"] .stRadio label:hover { color: #ffffff !important; }
section[data-testid="stSidebar"] h1 { color: #f8fafc !important; font-size: 1.4rem !important; letter-spacing: -0.02em; }
section[data-testid="stSidebar"] hr { border-color: #334155; }

/* ---- KPI card ---- */
.kpi-card {
    background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 24px 20px;
    text-align: center;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    transition: transform 0.15s, box-shadow 0.15s;
}
.kpi-card:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
.kpi-value { font-size: 2rem; font-weight: 700; color: #0f172a; line-height: 1; margin: 8px 0 4px; }
.kpi-label { font-size: 0.8rem; font-weight: 500; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; }
.kpi-icon { font-size: 1.6rem; }

/* ---- Section header ---- */
.section-header {
    font-size: 1.15rem;
    font-weight: 600;
    color: #1e293b;
    padding: 12px 0 8px;
    border-bottom: 2px solid #e2e8f0;
    margin-bottom: 16px;
}

/* ---- Alert card ---- */
.alert-card {
    border-left: 4px solid #94a3b8;
    border-radius: 8px;
    background: #ffffff;
    padding: 16px 20px;
    margin-bottom: 12px;
    box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    transition: box-shadow 0.15s;
}
.alert-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.08); }
.alert-card.bajista { border-left-color: #ef4444; }
.alert-card.alcista { border-left-color: #22c55e; }
.alert-card.neutral { border-left-color: #f59e0b; }

.alert-title { font-weight: 600; font-size: 0.95rem; color: #1e293b; margin-bottom: 8px; line-height: 1.3; }
.alert-meta { display: flex; gap: 16px; flex-wrap: wrap; align-items: center; margin-bottom: 8px; }
.alert-tag { display: inline-block; font-size: 0.72rem; font-weight: 600; padding: 3px 10px; border-radius: 20px; text-transform: uppercase; letter-spacing: 0.03em; }
.tag-bajista { background: #fef2f2; color: #dc2626; }
.tag-alcista { background: #f0fdf4; color: #16a34a; }
.tag-neutral { background: #fffbeb; color: #d97706; }
.tag-severity { background: #eff6ff; color: #2563eb; }
.tag-event { background: #f5f3ff; color: #7c3aed; }
.tag-source { background: #f0f9ff; color: #0369a1; }
.alert-explanation { font-size: 0.85rem; color: #475569; line-height: 1.5; padding: 10px 14px; background: #f8fafc; border-radius: 6px; margin-top: 8px; border: 1px solid #e2e8f0; }
.alert-assets { font-size: 0.82rem; color: #64748b; }
.alert-assets strong { color: #1e293b; }

/* ---- News card ---- */
.news-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 16px 20px;
    margin-bottom: 10px;
    transition: box-shadow 0.15s;
}
.news-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
.news-title { font-weight: 600; font-size: 0.9rem; color: #1e293b; }
.news-meta { font-size: 0.78rem; color: #94a3b8; margin-top: 4px; }
.news-summary { font-size: 0.84rem; color: #475569; margin-top: 6px; line-height: 1.5; }

/* ---- Source card ---- */
.source-card {
    background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 14px 18px;
    text-align: center;
}
.source-name { font-weight: 600; font-size: 0.9rem; color: #1e293b; }
.source-type { font-size: 0.75rem; color: #64748b; }

/* ---- Button overrides ---- */
.stButton > button {
    border-radius: 8px !important;
    font-weight: 600 !important;
    border: 1px solid #e2e8f0 !important;
    transition: all 0.15s !important;
}
div[data-testid="stForm"] .stButton > button[kind="secondaryFormSubmit"] {
    background: #0f172a !important;
    color: #ffffff !important;
    border: none !important;
}
div[data-testid="stForm"] .stButton > button[kind="secondaryFormSubmit"]:hover {
    background: #1e293b !important;
}

/* ---- DataFrames ---- */
.stDataFrame { border-radius: 8px; overflow: hidden; }

/* ---- Pipeline result banner ---- */
.pipeline-result {
    display: flex;
    gap: 12px;
    justify-content: center;
    padding: 16px;
    background: #f0fdf4;
    border: 1px solid #bbf7d0;
    border-radius: 10px;
    margin: 12px 0;
}
.pipeline-stat {
    text-align: center;
    padding: 0 16px;
    border-right: 1px solid #d1fae5;
}
.pipeline-stat:last-child { border-right: none; }
.pipeline-stat .num { font-size: 1.5rem; font-weight: 700; color: #166534; }
.pipeline-stat .lbl { font-size: 0.72rem; color: #4ade80; text-transform: uppercase; font-weight: 600; }

/* ---- Tabbed nav pills (override Streamlit tabs) ---- */
.stTabs [data-baseweb="tab-list"] { gap: 4px; }
.stTabs [data-baseweb="tab"] { border-radius: 8px 8px 0 0; font-weight: 600; }

/* ---- Hide Streamlit footer ---- */
footer { visibility: hidden; }
#MainMenu { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
if "portfolio_id" not in st.session_state:
    st.session_state.portfolio_id = ""
if "user_id" not in st.session_state:
    st.session_state.user_id = "default_user"
if "selected_portfolio_name" not in st.session_state:
    st.session_state.selected_portfolio_name = ""

# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------
def api_get(endpoint: str, params: dict | None = None):
    try:
        r = requests.get(f"{API_BASE}{endpoint}", params=params, timeout=30)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        st.error("No se puede conectar con el backend. Asegúrate de que la API esté corriendo.")
        return None
    except Exception as e:
        st.error(f"Error de API: {e}")
        return None


def api_post(endpoint: str, json_data: dict | None = None, params: dict | None = None):
    try:
        r = requests.post(f"{API_BASE}{endpoint}", json=json_data, params=params, timeout=120)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        st.error("No se puede conectar con el backend.")
        return None
    except Exception as e:
        st.error(f"Error de API: {e}")
        return None


# ---------------------------------------------------------------------------
# Reusable components
# ---------------------------------------------------------------------------
def kpi_card(icon: str, value: str, label: str):
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-icon">{icon}</div>
        <div class="kpi-value">{value}</div>
        <div class="kpi-label">{label}</div>
    </div>
    """, unsafe_allow_html=True)


def section_header(text: str):
    st.markdown(f'<div class="section-header">{text}</div>', unsafe_allow_html=True)


def render_alert_card(alert: dict):
    direction = alert.get("direction", "neutral")
    severity_label = alert.get("severity_label", "media")
    event_type = alert.get("event_type", "otro").replace("_", " ").title()
    source = alert.get("news_source", "")
    severity = alert.get("severity", 0)
    confidence = alert.get("confidence", 0)
    assets = ", ".join(alert.get("matched_assets", []))
    title = alert.get("news_title", "Sin título")
    explanation = alert.get("explanation", "")
    url = alert.get("news_url", "")
    created = alert.get("created_at", "")
    if created:
        try:
            dt = datetime.fromisoformat(created)
            created = dt.strftime("%d %b %Y · %H:%M")
        except Exception:
            pass

    dir_class = direction if direction in ("bajista", "alcista", "neutral") else "neutral"

    st.markdown(f"""
    <div class="alert-card {dir_class}">
        <div class="alert-title">{title}</div>
        <div class="alert-meta">
            <span class="alert-tag tag-{dir_class}">{direction.upper()}</span>
            <span class="alert-tag tag-severity">Severidad {severity:.0%}</span>
            <span class="alert-tag tag-event">{event_type}</span>
            <span class="alert-tag tag-source">{source}</span>
        </div>
        <div class="alert-assets"><strong>Activos:</strong> {assets} &nbsp;|&nbsp; <strong>Confianza:</strong> {confidence:.0%} &nbsp;|&nbsp; {created}</div>
        <div class="alert-explanation">{explanation}</div>
        {"<div style='margin-top:8px'><a href='" + url + "' target='_blank' style='font-size:0.8rem;color:#2563eb;text-decoration:none;font-weight:500'>Ver fuente original →</a></div>" if url else ""}
    </div>
    """, unsafe_allow_html=True)


def render_news_card(item: dict):
    title = item.get("title", "Sin título")
    source = item.get("source", "")
    stype = item.get("source_type", "")
    published = item.get("published_at", "")
    lang = item.get("language", "")
    summary = (item.get("summary") or "")[:280]
    url = item.get("url", "")
    if published:
        try:
            dt = datetime.fromisoformat(published)
            published = dt.strftime("%d %b %Y · %H:%M")
        except Exception:
            pass

    st.markdown(f"""
    <div class="news-card">
        <div class="news-title">{title}</div>
        <div class="news-meta">{source} · {stype} · {published} · {lang.upper() if lang else ''}</div>
        {"<div class='news-summary'>" + summary + "</div>" if summary else ""}
        {"<div style='margin-top:6px'><a href='" + url + "' target='_blank' style='font-size:0.78rem;color:#2563eb;text-decoration:none;font-weight:500'>Leer más →</a></div>" if url else ""}
    </div>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("""
    <div style="padding: 8px 0 4px;">
        <span style="font-size:1.6rem;font-weight:700;color:#f8fafc;letter-spacing:-0.03em">⚡ InvestAlert</span>
        <br><span style="font-size:0.75rem;color:#94a3b8">Alertas Inteligentes por NLP</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    page = st.radio(
        "Navegación",
        ["Dashboard", "Cartera", "Noticias", "Motor de Alertas", "Configuración"],
        format_func=lambda x: {
            "Dashboard": "📊  Dashboard",
            "Cartera": "💼  Cartera",
            "Noticias": "📰  Noticias",
            "Motor de Alertas": "⚡  Motor de Alertas",
            "Configuración": "⚙️  Configuración",
        }[x],
    )

    st.markdown("---")

    # Portfolio selector in sidebar
    st.markdown('<span style="font-size:0.78rem;color:#94a3b8;text-transform:uppercase;letter-spacing:0.05em;font-weight:600">Cartera activa</span>', unsafe_allow_html=True)
    portfolios_sidebar = api_get("/api/portfolios", params={"user_id": st.session_state.user_id})
    if portfolios_sidebar:
        portfolio_names = {p.get("_id", ""): p.get("name", "Sin nombre") for p in portfolios_sidebar}
        options = list(portfolio_names.keys())
        names = list(portfolio_names.values())

        if st.session_state.portfolio_id in options:
            default_idx = options.index(st.session_state.portfolio_id)
        elif options:
            default_idx = 0
        else:
            default_idx = 0

        if options:
            selected = st.selectbox(
                "Seleccionar cartera",
                options=options,
                index=default_idx,
                format_func=lambda x: portfolio_names.get(x, x),
                label_visibility="collapsed",
            )
            st.session_state.portfolio_id = selected
            st.session_state.selected_portfolio_name = portfolio_names.get(selected, "")
    else:
        st.caption("Sin carteras creadas")

    st.markdown("---")

    # Backend status
    health = api_get("/health")
    if health:
        st.markdown('<span style="color:#4ade80;font-size:0.8rem">● Backend conectado</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span style="color:#f87171;font-size:0.8rem">● Backend desconectado</span>', unsafe_allow_html=True)


# ===================================================================
# DASHBOARD
# ===================================================================
if page == "Dashboard":
    st.markdown("## 📊 Dashboard")
    if st.session_state.selected_portfolio_name:
        st.caption(f"Cartera activa: **{st.session_state.selected_portfolio_name}**")

    # --- KPIs ---
    pid = st.session_state.portfolio_id
    stats = api_get("/api/alerts/stats", params={"portfolio_id": pid} if pid else None)
    news_count_data = api_get("/api/news", params={"limit": 1})
    alerts_data = api_get("/api/alerts", params={"portfolio_id": pid, "limit": 100} if pid else {"limit": 100})

    total_alerts = stats.get("total", 0) if stats else 0
    avg_severity = stats.get("avg_severity", 0) if stats else 0
    avg_confidence = stats.get("avg_confidence", 0) if stats else 0

    # Count directions
    n_bajista = n_alcista = n_neutral = 0
    if alerts_data:
        for a in alerts_data:
            d = a.get("direction", "")
            if d == "bajista":
                n_bajista += 1
            elif d == "alcista":
                n_alcista += 1
            else:
                n_neutral += 1

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        kpi_card("⚡", str(total_alerts), "Total Alertas")
    with c2:
        kpi_card("📉", str(n_bajista), "Bajistas")
    with c3:
        kpi_card("📈", str(n_alcista), "Alcistas")
    with c4:
        kpi_card("🎯", f"{avg_severity:.0%}" if avg_severity else "—", "Severidad Media")
    with c5:
        kpi_card("🔒", f"{avg_confidence:.0%}" if avg_confidence else "—", "Confianza Media")

    st.markdown("<br>", unsafe_allow_html=True)

    # --- Charts ---
    if alerts_data:
        df = pd.DataFrame(alerts_data)

        col_left, col_right = st.columns(2)

        with col_left:
            section_header("Distribución por Tipo de Evento")
            if "event_type" in df.columns:
                event_counts = df["event_type"].value_counts().reset_index()
                event_counts.columns = ["Tipo", "Cantidad"]
                fig = px.bar(
                    event_counts, x="Cantidad", y="Tipo", orientation="h",
                    color="Cantidad",
                    color_continuous_scale=["#c7d2fe", "#4f46e5"],
                )
                fig.update_layout(
                    margin=dict(l=0, r=0, t=10, b=0), height=300,
                    showlegend=False, coloraxis_showscale=False,
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                    yaxis=dict(autorange="reversed"),
                    font=dict(family="Inter", size=12),
                )
                fig.update_traces(marker_line_width=0)
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        with col_right:
            section_header("Dirección del Impacto")
            if "direction" in df.columns:
                dir_counts = df["direction"].value_counts().reset_index()
                dir_counts.columns = ["Dirección", "Cantidad"]
                color_map = {"bajista": "#ef4444", "alcista": "#22c55e", "neutral": "#f59e0b"}
                fig2 = px.pie(
                    dir_counts, values="Cantidad", names="Dirección",
                    color="Dirección", color_discrete_map=color_map,
                    hole=0.55,
                )
                fig2.update_layout(
                    margin=dict(l=0, r=0, t=10, b=0), height=300,
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(family="Inter", size=12),
                    legend=dict(orientation="h", y=-0.15, x=0.5, xanchor="center"),
                )
                fig2.update_traces(textinfo="percent+value", textfont_size=13)
                st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

        # Severity distribution
        section_header("Distribución de Severidad")
        if "severity" in df.columns:
            fig3 = px.histogram(
                df, x="severity", nbins=20,
                color_discrete_sequence=["#6366f1"],
                labels={"severity": "Severidad", "count": "Frecuencia"},
            )
            fig3.update_layout(
                margin=dict(l=0, r=0, t=10, b=0), height=220,
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                bargap=0.08,
                font=dict(family="Inter", size=12),
                xaxis=dict(range=[0, 1]),
            )
            fig3.update_traces(marker_line_width=0)
            st.plotly_chart(fig3, use_container_width=True, config={"displayModeBar": False})

    st.markdown("<br>", unsafe_allow_html=True)

    # --- Recent alerts ---
    section_header("Últimas Alertas")
    recent = api_get("/api/alerts", params={"portfolio_id": pid, "limit": 8} if pid else {"limit": 8})
    if recent:
        for alert in recent:
            render_alert_card(alert)
    else:
        st.info("No hay alertas aún. Ingesta noticias y procésa las contra tu cartera para empezar.")


# ===================================================================
# CARTERA
# ===================================================================
elif page == "Cartera":
    st.markdown("## 💼 Gestión de Cartera")

    tab_view, tab_create, tab_add = st.tabs(["📋 Mis Carteras", "➕ Nueva Cartera", "🔗 Añadir Activo"])

    # --- Tab: mis carteras ---
    with tab_view:
        portfolios = api_get("/api/portfolios", params={"user_id": st.session_state.user_id})
        if portfolios:
            for p in portfolios:
                pname = p.get("name", "Sin nombre")
                pid = p.get("_id", "")
                assets = p.get("assets", [])

                with st.container():
                    c1, c2 = st.columns([4, 1])
                    c1.markdown(f"### {pname}")
                    c2.code(pid, language=None)

                if assets:
                    df = pd.DataFrame(assets)
                    display_cols = [c for c in ["ticker", "name", "sector", "country", "weight"] if c in df.columns]
                    df_display = df[display_cols].copy()
                    if "weight" in df_display.columns:
                        df_display["weight"] = df_display["weight"].apply(lambda x: f"{x:.0%}")
                        df_display = df_display.rename(columns={"weight": "Peso", "ticker": "Ticker", "name": "Nombre", "sector": "Sector", "country": "País"})

                    st.dataframe(df_display, use_container_width=True, hide_index=True)

                    # Weight pie chart
                    if "weight" in df.columns and len(df) > 1:
                        fig = px.pie(
                            df, values="weight", names="ticker",
                            color_discrete_sequence=px.colors.qualitative.Set3,
                            hole=0.4,
                        )
                        fig.update_layout(
                            margin=dict(l=0, r=0, t=20, b=0), height=250,
                            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                            font=dict(family="Inter", size=11),
                            legend=dict(orientation="h", y=-0.2, x=0.5, xanchor="center"),
                            title=dict(text="Distribución de pesos", font=dict(size=13, color="#64748b")),
                        )
                        fig.update_traces(textinfo="label+percent", textfont_size=11)
                        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

                    # Sector breakdown
                    if "sector" in df.columns:
                        sector_counts = df["sector"].value_counts()
                        sector_weights = df.groupby("sector")["weight"].sum()
                        if len(sector_counts) > 1:
                            sec_df = pd.DataFrame({"Sector": sector_weights.index, "Peso": sector_weights.values})
                            fig2 = px.bar(
                                sec_df, x="Sector", y="Peso",
                                color_discrete_sequence=["#6366f1"],
                            )
                            fig2.update_layout(
                                margin=dict(l=0, r=0, t=20, b=0), height=200,
                                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                                font=dict(family="Inter", size=11),
                                title=dict(text="Peso por sector", font=dict(size=13, color="#64748b")),
                                yaxis=dict(tickformat=".0%"),
                            )
                            fig2.update_traces(marker_line_width=0)
                            st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})
                else:
                    st.caption("Sin activos todavía.")

                st.markdown("---")
        else:
            st.info("No tienes carteras creadas. Ve a la pestaña **Nueva Cartera** para crear una.")

    # --- Tab: crear cartera ---
    with tab_create:
        section_header("Crear nueva cartera")
        with st.form("create_portfolio", clear_on_submit=True):
            c1, c2 = st.columns(2)
            name = c1.text_input("Nombre de la cartera", placeholder="Mi Cartera Tecnológica")
            user_id = c2.text_input("User ID", value=st.session_state.user_id)
            submitted = st.form_submit_button("Crear Cartera", use_container_width=True)
            if submitted and name:
                result = api_post("/api/portfolios", {"user_id": user_id, "name": name})
                if result:
                    st.session_state.portfolio_id = result.get("portfolio_id", "")
                    st.success(f"Cartera «{name}» creada correctamente.")
                    st.rerun()

    # --- Tab: añadir activo ---
    with tab_add:
        section_header("Añadir activo a cartera activa")
        if not st.session_state.portfolio_id:
            st.warning("Selecciona una cartera en la barra lateral primero.")
        else:
            st.caption(f"Cartera: **{st.session_state.selected_portfolio_name}** (`{st.session_state.portfolio_id}`)")
            with st.form("add_asset", clear_on_submit=True):
                c1, c2 = st.columns(2)
                ticker = c1.text_input("Ticker", placeholder="AAPL")
                name = c2.text_input("Nombre completo", placeholder="Apple Inc.")
                c3, c4, c5 = st.columns(3)
                sector = c3.text_input("Sector", placeholder="Technology")
                country = c4.text_input("País (ISO 2)", placeholder="US")
                weight = c5.number_input("Peso (0–1)", min_value=0.0, max_value=1.0, value=0.10, step=0.05)
                aliases = st.text_input("Aliases (separados por coma)", placeholder="Apple, AAPL US Equity")

                submitted = st.form_submit_button("Añadir Activo", use_container_width=True)
                if submitted and ticker:
                    alias_list = [a.strip() for a in aliases.split(",") if a.strip()]
                    result = api_post(
                        f"/api/portfolios/{st.session_state.portfolio_id}/assets",
                        {"ticker": ticker, "name": name, "sector": sector, "country": country, "weight": weight, "aliases": alias_list},
                    )
                    if result:
                        st.success(f"**{ticker}** añadido a la cartera.")
                        st.rerun()


# ===================================================================
# NOTICIAS
# ===================================================================
elif page == "Noticias":
    st.markdown("## 📰 Adquisición de Noticias")

    tab_ingest, tab_browse = st.tabs(["🔄 Ingestar", "📋 Explorar Noticias"])

    with tab_ingest:
        section_header("Fuentes primarias (sin API key)")
        c1, c2, c3 = st.columns(3)

        with c1:
            st.markdown("""
            <div class="source-card">
                <div class="source-name">📡 Todas las fuentes</div>
                <div class="source-type">RSS + SEC + CNMV</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Ingestar todo", key="ingest_all", use_container_width=True):
                with st.spinner("Ingesta en progreso — todas las fuentes..."):
                    result = api_post("/api/ingest")
                if result:
                    st.success(f"Completado: {result.get('stats', result)}")

        with c2:
            st.markdown("""
            <div class="source-card">
                <div class="source-name">📡 RSS Feeds</div>
                <div class="source-type">22 feeds · finanzas, macro, cyber, supply chain, prensa ES</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Solo RSS", key="ingest_rss", use_container_width=True):
                with st.spinner("Descargando feeds RSS..."):
                    result = api_post("/api/ingest/rss")
                if result:
                    st.success(f"{result.get('count', 0)} noticias nuevas")

        with c3:
            st.markdown("""
            <div class="source-card">
                <div class="source-name">🇪🇸 CNMV</div>
                <div class="source-type">Hechos relevantes · info privilegiada</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Solo CNMV", key="ingest_cnmv", use_container_width=True):
                with st.spinner("Descargando CNMV..."):
                    result = api_post("/api/ingest/cnmv")
                if result:
                    st.success(f"{result.get('count', 0)} noticias nuevas")

        st.markdown("<br>", unsafe_allow_html=True)
        section_header("Fuentes enriquecidas (requieren API key gratuita)")

        c4, c5 = st.columns(2)
        with c4:
            st.markdown("""
            <div class="source-card">
                <div class="source-name">🌐 NewsAPI.org</div>
                <div class="source-type">Texto completo · +150k fuentes globales</div>
            </div>
            """, unsafe_allow_html=True)
            newsapi_query = st.text_input("Buscar en NewsAPI", placeholder="Apple earnings OR Tesla regulation", label_visibility="collapsed")
            if st.button("Buscar en NewsAPI", key="ingest_newsapi", use_container_width=True):
                if newsapi_query:
                    with st.spinner("Buscando en NewsAPI..."):
                        result = api_post("/api/ingest/newsapi", params={"query": newsapi_query})
                    if result:
                        st.success(f"{result.get('count', 0)} noticias encontradas")
                else:
                    st.warning("Introduce un término de búsqueda")

        with c5:
            st.markdown("""
            <div class="source-card">
                <div class="source-name">📈 Alpha Vantage</div>
                <div class="source-type">Tickers anotados · sentiment pre-calculado</div>
            </div>
            """, unsafe_allow_html=True)
            av_tickers = st.text_input("Tickers (separados por coma)", placeholder="AAPL,MSFT,TSLA", label_visibility="collapsed")
            if st.button("Buscar en Alpha Vantage", key="ingest_av", use_container_width=True):
                if av_tickers:
                    with st.spinner("Buscando en Alpha Vantage..."):
                        result = api_post("/api/ingest/alphavantage", params={"tickers": av_tickers})
                    if result:
                        st.success(f"{result.get('count', 0)} noticias encontradas")
                else:
                    st.warning("Introduce tickers separados por coma")

    with tab_browse:
        section_header("Noticias almacenadas")
        limit = st.select_slider("Mostrar", options=[20, 50, 100, 200], value=50)
        news = api_get("/api/news", params={"limit": limit})
        if news:
            st.caption(f"Mostrando {len(news)} noticias más recientes")
            for item in news:
                render_news_card(item)
        else:
            st.info("No hay noticias almacenadas. Usa la pestaña **Ingestar** para adquirir noticias.")


# ===================================================================
# MOTOR DE ALERTAS
# ===================================================================
elif page == "Motor de Alertas":
    st.markdown("## ⚡ Motor de Alertas")

    tab_batch, tab_manual, tab_history = st.tabs(["🚀 Procesar Batch", "✍️ Análisis Manual", "📋 Historial"])

    # --- Batch processing ---
    with tab_batch:
        pid = st.session_state.portfolio_id
        if not pid:
            st.warning("Selecciona una cartera activa en la barra lateral.")
        else:
            section_header(f"Pipeline NLP → {st.session_state.selected_portfolio_name}")
            st.caption("Procesa noticias recientes a través del pipeline completo: NLP → Relevancia → Clasificación → Impacto → Dedup → Alerta")

            c1, c2 = st.columns([3, 1])
            batch_limit = c1.slider("Noticias a procesar", 10, 200, 50, step=10)
            with c2:
                st.markdown("<br>", unsafe_allow_html=True)
                run = st.button("▶  Ejecutar Pipeline", use_container_width=True, type="primary")

            if run:
                with st.spinner("Procesando noticias por el pipeline NLP completo..."):
                    result = api_post(f"/api/alerts/process-batch/{pid}", params={"limit": batch_limit})
                if result:
                    processed = result.get("processed", 0)
                    generated = result.get("alerts_generated", 0)
                    duplicates = result.get("duplicates", 0)
                    discarded = result.get("discarded", 0)

                    st.markdown(f"""
                    <div class="pipeline-result">
                        <div class="pipeline-stat"><div class="num">{processed}</div><div class="lbl">Procesadas</div></div>
                        <div class="pipeline-stat"><div class="num">{generated}</div><div class="lbl">Alertas</div></div>
                        <div class="pipeline-stat"><div class="num">{duplicates}</div><div class="lbl">Duplicados</div></div>
                        <div class="pipeline-stat"><div class="num">{discarded}</div><div class="lbl">Descartadas</div></div>
                    </div>
                    """, unsafe_allow_html=True)

                    if generated > 0:
                        st.markdown("<br>", unsafe_allow_html=True)
                        section_header("Alertas generadas en este batch")
                        new_alerts = api_get("/api/alerts", params={"portfolio_id": pid, "limit": generated})
                        if new_alerts:
                            for a in new_alerts:
                                render_alert_card(a)

    # --- Manual analysis ---
    with tab_manual:
        section_header("Analizar noticia individual")
        st.caption("Introduce manualmente una noticia para analizarla contra la cartera activa.")

        with st.form("manual_news", clear_on_submit=False):
            title = st.text_input("Titular", placeholder="Apple reports lower than expected Q2 earnings amid China slowdown")
            summary = st.text_area("Resumen / cuerpo", placeholder="Pega aquí el texto de la noticia...", height=120)
            c1, c2 = st.columns(2)
            source = c1.text_input("Fuente", value="manual")
            url = c2.text_input("URL (opcional)", placeholder="https://...")

            submitted = st.form_submit_button("Analizar noticia", use_container_width=True)
            if submitted and title:
                with st.spinner("Analizando..."):
                    result = api_post("/api/alerts/process", {
                        "title": title, "summary": summary, "content": "", "url": url,
                        "source": source, "portfolio_id": st.session_state.portfolio_id,
                    })
                if result:
                    if result.get("status") == "alert_generated":
                        st.success("Alerta generada")
                        render_alert_card(result["alert"])
                    else:
                        reason = result.get("reason", "No superó los umbrales del pipeline")
                        st.info(f"Sin alerta: {reason}")

    # --- Historical ---
    with tab_history:
        pid = st.session_state.portfolio_id
        section_header("Historial de alertas")
        alerts = api_get("/api/alerts", params={"portfolio_id": pid, "limit": 200} if pid else {"limit": 200})
        if alerts:
            df = pd.DataFrame(alerts)

            # Summary table
            if not df.empty:
                cols_map = {
                    "news_title": "Titular",
                    "event_type": "Evento",
                    "direction": "Dirección",
                    "severity_label": "Severidad",
                    "severity": "Score",
                    "confidence": "Confianza",
                    "matched_assets": "Activos",
                    "news_source": "Fuente",
                }
                available = {k: v for k, v in cols_map.items() if k in df.columns}
                df_show = df[list(available.keys())].rename(columns=available)
                if "Score" in df_show.columns:
                    df_show["Score"] = df_show["Score"].apply(lambda x: f"{x:.2f}")
                if "Confianza" in df_show.columns:
                    df_show["Confianza"] = df_show["Confianza"].apply(lambda x: f"{x:.2f}")
                if "Activos" in df_show.columns:
                    df_show["Activos"] = df_show["Activos"].apply(lambda x: ", ".join(x) if isinstance(x, list) else str(x))

                st.dataframe(df_show, use_container_width=True, hide_index=True, height=400)

            # Charts
            col_l, col_r = st.columns(2)
            with col_l:
                if "event_type" in df.columns:
                    event_counts = df["event_type"].value_counts().reset_index()
                    event_counts.columns = ["Tipo", "Cantidad"]
                    fig = px.bar(
                        event_counts, x="Cantidad", y="Tipo", orientation="h",
                        color_discrete_sequence=["#6366f1"],
                    )
                    fig.update_layout(
                        margin=dict(l=0, r=0, t=30, b=0), height=280,
                        title="Por tipo de evento",
                        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                        yaxis=dict(autorange="reversed"),
                        font=dict(family="Inter", size=11),
                    )
                    fig.update_traces(marker_line_width=0)
                    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

            with col_r:
                if "severity" in df.columns and "confidence" in df.columns:
                    color_map = {"bajista": "#ef4444", "alcista": "#22c55e", "neutral": "#f59e0b"}
                    fig2 = px.scatter(
                        df, x="severity", y="confidence",
                        color="direction", color_discrete_map=color_map,
                        hover_data=["news_title", "event_type"],
                        labels={"severity": "Severidad", "confidence": "Confianza", "direction": "Dirección"},
                    )
                    fig2.update_layout(
                        margin=dict(l=0, r=0, t=30, b=0), height=280,
                        title="Severidad vs. Confianza",
                        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                        font=dict(family="Inter", size=11),
                        xaxis=dict(range=[0, 1]), yaxis=dict(range=[0, 1]),
                    )
                    st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("No hay alertas en el historial.")


# ===================================================================
# CONFIGURACIÓN
# ===================================================================
elif page == "Configuración":
    st.markdown("## ⚙️ Configuración del Sistema")

    tab_status, tab_taxonomy, tab_sources = st.tabs(["🔌 Estado", "📚 Taxonomía", "📡 Fuentes"])

    with tab_status:
        section_header("Estado del Backend")
        health = api_get("/health")
        if health:
            st.success("Backend conectado y operativo")
        else:
            st.error("Backend no disponible — ejecuta `python main.py`")

        st.markdown("<br>", unsafe_allow_html=True)
        section_header("Umbrales del Pipeline")

        import config as cfg
        thresholds = {
            "Relevancia mínima": (cfg.RELEVANCE_THRESHOLD, "Noticias con score menor se descartan"),
            "Severidad mínima": (cfg.SEVERITY_THRESHOLD, "Impactos con severidad menor no generan alerta"),
            "Similitud deduplicación": (cfg.DEDUP_SIMILARITY_THRESHOLD, "Por encima se considera duplicado semántico"),
            "Máx. alertas/hora": (cfg.MAX_ALERTS_PER_HOUR, "Control anti-spam"),
        }
        cols = st.columns(len(thresholds))
        for i, (label, (val, desc)) in enumerate(thresholds.items()):
            with cols[i]:
                st.metric(label, val)
                st.caption(desc)

    with tab_taxonomy:
        section_header("Taxonomía de Eventos Financieros")
        from modules.events.classifier import EVENT_DESCRIPTIONS

        taxonomy_data = []
        direction_hints = {
            "resultados_empresariales": "Variable",
            "guidance_profit_warning": "↓ Bajista",
            "regulacion": "↓ Bajista",
            "litigio": "↓ Bajista",
            "fusion_adquisicion": "Variable",
            "ciberincidente": "↓↓ Muy bajista",
            "incidencia_operativa": "↓ Bajista",
            "macroeconomia": "Variable",
            "cadena_suministro": "↓ Bajista",
            "cambio_directivo": "Variable",
            "dividendo_recompra": "↑ Alcista",
            "otro": "Neutral",
        }
        for event, desc in EVENT_DESCRIPTIONS.items():
            taxonomy_data.append({
                "Categoría": event.replace("_", " ").title(),
                "Descripción": desc,
                "Tendencia": direction_hints.get(event, "—"),
            })
        st.dataframe(pd.DataFrame(taxonomy_data), use_container_width=True, hide_index=True, height=480)

    with tab_sources:
        section_header("Fuentes de Datos Configuradas")

        import config as cfg

        st.markdown("**RSS Feeds — Finanzas generales, macro, cyberseguridad, supply chain, prensa española**")
        rss_data = [{"Nombre": name, "URL": url} for name, url in cfg.RSS_FEEDS.items()]
        st.dataframe(pd.DataFrame(rss_data), use_container_width=True, hide_index=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("**CNMV — Comisión Nacional del Mercado de Valores**")
        cnmv_data = [{"Nombre": name, "URL": url} for name, url in cfg.CNMV_RSS_FEEDS.items()]
        st.dataframe(pd.DataFrame(cnmv_data), use_container_width=True, hide_index=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("**APIs enriquecidas**")
        api_sources = [
            {"Fuente": "NewsAPI.org", "Estado": "✅ Configurada" if getattr(cfg, "NEWSAPI_KEY", "") else "⚠️ Sin API key", "Límite": "100 req/día (gratis)"},
            {"Fuente": "Alpha Vantage", "Estado": "✅ Configurada" if getattr(cfg, "ALPHAVANTAGE_KEY", "") else "⚠️ Sin API key", "Límite": "25 req/día (gratis)"},
            {"Fuente": "OpenAI (clasificación)", "Estado": "✅ Configurada" if getattr(cfg, "OPENAI_API_KEY", "") else "⚠️ Usando fallback keywords", "Límite": "Pay-as-you-go"},
        ]
        st.dataframe(pd.DataFrame(api_sources), use_container_width=True, hide_index=True)
