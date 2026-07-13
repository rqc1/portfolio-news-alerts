# InvestAIlert — Sistema de Alertas Inteligentes por Noticias para Carteras de Inversión

> **TFM** — Máster en Inteligencia Artificial / Ciencia de Datos aplicada a Finanzas (UNIR, 2026)

Sistema que monitoriza flujos de noticias financieras heterogéneos, detecta eventos
materialmente relevantes para una cartera de inversión concreta, estima la dirección
y severidad del impacto y emite alertas explicables con control de ruido, deduplicación
semántica y trazabilidad de fuente.

---

## Motivación y Contexto Académico

La inversión financiera contemporánea se enfrenta a una sobreabundancia informativa:
el inversor ya no necesita *acceder* a la información, sino *discriminar* cuál es
realmente material para sus posiciones. Este proyecto cierra una brecha detectada en
la literatura entre tres líneas de investigación activas que rara vez convergen:

| Línea | Qué aporta | Qué le falta |
|-------|-----------|--------------|
| **Robo-advisors** | Personalización financiera, perfilado de riesgo | No leen noticias ni detectan eventos |
| **NLP financiero** | Extracción de señal desde texto (sentimiento, entidades) | Evalúa tareas aisladas, no integradas por cartera |
| **Agentes LLM** | Razonamiento flexible y uso de herramientas | Coste, evaluación frágil, gobernanza compleja |

El sistema propuesto ocupa una **posición intermedia deliberada**: adopta la lógica de
personalización de los robo-advisors, toma del NLP financiero sus mecanismos de
extracción de señal y se mantiene prudente frente a la complejidad de los agentes
autónomos. No sustituye al inversor; mejora de forma medible la calidad, oportunidad
y explicabilidad de la información que recibe.

> Referencia completa del marco teórico en `TFM_alertas_inversion_estado_de_la_cuestion.pdf`

---

## Arquitectura del Pipeline

```
┌─────────────┐    ┌───────────────┐    ┌──────────────┐    ┌──────────────────┐
│  1. CARTERA  │───▸│  2. INGESTA   │───▸│  3. NLP      │───▸│  4. RELEVANCIA   │
│  Portfolio   │    │  SEC / CNMV / │    │  Limpieza +  │    │  Reglas +        │
│  Tickers,    │    │  RSS / NewsAPI │    │  NER + Lang  │    │  Embeddings      │
│  Sectores,   │    │  Alpha Vantage│    │  Detection   │    │  Semánticos      │
│  Geografías  │    └───────────────┘    └──────────────┘    └────────┬─────────┘
└─────────────┘                                                       │
                                                    ┌─────────────────┤
                                                    ▼                 ▼ (borderline)
┌───────────────────────────────────────────────┐  ┌─────────────────────────────┐
│           5. CLASIFICACIÓN DE EVENTOS         │  │  4b. LLM RELEVANCE CHECK   │
│  FinBERT (sentiment) + Zero-shot NLI (tipo)   │  │  Relevancia indirecta:      │
│  [local, sin coste API]                       │  │  competidores, proveedores, │
└──────────────────────┬────────────────────────┘  │  regulación sectorial       │
                       │                           └─────────────────────────────┘
                       ▼
┌──────────────────┐    ┌──────────────────────────────────────────────────────┐
│  6. ESTIMACIÓN   │───▸│  7. MOTOR DE ALERTAS                                │
│  DE IMPACTO      │    │  Análisis contextual LLM (multi-proveedor) ·        │
│  Determinista +  │    │  Impacto + explicación contextualizada a cartera ·  │
│  LLM contextual  │    │  Deduplicación semántica · Anti-spam               │
└──────────────────┘    └──────────────────────────────────────────────────────┘
```

Cada módulo se documenta mediante docstrings en su código fuente (`modules/<módulo>/`).

---

## Stack Tecnológico

| Capa | Tecnología | Rol |
|------|-----------|-----|
| **API** | FastAPI + Uvicorn | Backend REST asíncrono |
| **Frontend** | Next.js 16 + React 19 / Streamlit (legacy) | Dashboard interactivo para gestión y visualización |
| **Base de datos** | MongoDB (Motor async) | Almacenamiento de noticias, carteras y alertas |
| **Sentiment** | FinBERT (`ProsusAI/finbert`) | Análisis de sentimiento financiero |
| **Embeddings** | Sentence-Transformers (`all-MiniLM-L6-v2`) | Similitud semántica y deduplicación |
| **NER** | spaCy (`en_core_web_sm`) | Reconocimiento de entidades nombradas |
| **Clasificación eventos** | Zero-shot NLI (`facebook/bart-large-mnli`) + fallback keywords | Tipo de evento financiero (local, sin coste API) |
| **Análisis contextual** | LLM multi-proveedor (GitHub Models / HuggingFace / OpenAI / Ollama) | Impacto contextualizado + explicaciones personalizadas |
| **Traducción** | deep-translator (`GoogleTranslator`) | Traducción automática ES→EN para noticias CNMV |
| **Ingesta** | feedparser + httpx | RSS, SEC EDGAR, CNMV, NewsAPI, Alpha Vantage |
| **Datos mercado** | yfinance ≥1.3 | Precios, históricos, lookup de activos (Yahoo Finance) |
| **Analytics cartera** | quantstats ≥0.0.62 | Sharpe, Sortino, VaR, drawdown, alpha/beta |

---

## Estructura del Proyecto

```
TFE/
│
├── config.py                          # Configuración central (modelos, fuentes, umbrales)
├── main.py                            # API REST (FastAPI) — punto de entrada del backend
├── app.py                             # Dashboard (Streamlit) — interfaz de usuario
├── requirements.txt                   # Dependencias Python
├── Dockerfile                         # Multi-stage build (builder + runtime)
├── docker-compose.yml                 # MongoDB + API + Frontend en un comando
├── .dockerignore                      # Exclusiones para Docker build
├── .env.example                       # Template de variables de entorno
│
├── database/
│   ├── __init__.py
│   └── mongodb.py                     # Conexión async, colecciones, índices
│
├── modules/
│   ├── portfolio/                     # Módulo 1 — Modelado de cartera
│   │   ├── models.py                  #   Schemas: Asset, Portfolio
│   │   └── service.py                 #   CRUD sobre MongoDB
│   │
│   ├── ingestion/                     # Módulo 2 — Adquisición de noticias
│   │   ├── models.py                  #   Schema: NewsItem
│   │   ├── rss_feeds.py              #   22 feeds RSS (finanzas, macro, cyber, supply chain)
│   │   ├── sec_edgar.py              #   SEC EDGAR API (8-K, 10-K, 10-Q)
│   │   ├── cnmv.py                   #   CNMV RSS (hechos relevantes, info privilegiada)
│   │   ├── newsapi.py                #   NewsAPI.org (texto completo, +150k fuentes)
│   │   ├── alphavantage.py           #   Alpha Vantage (tickers anotados + sentimiento)
│   │   └── service.py                #   Orquestador: ingesta + dedup por hash + persistencia
│   │
│   ├── nlp/                           # Módulo 3 — Preprocesado NLP
│   │   ├── preprocessing.py          #   Limpieza, NER, detección de idioma, traducción ES→EN
│   │   └── entity_resolver.py        #   Resolución canónica de entidades (alias → ticker)
│   │
│   ├── relevance/                     # Módulo 4 — Relevancia por cartera
│   │   └── service.py                #   Reglas explícitas (word-boundary matching) + similitud semántica por activo
│   │
│   ├── events/                        # Módulo 5 — Clasificación de eventos
│   │   └── classifier.py             #   FinBERT + zero-shot NLI + keyword fallback
│   │
│   ├── impact/                        # Módulo 6 — Estimación de impacto
│   │   ├── estimator.py              #   Determinista + guardrails + merge con análisis LLM contextual
│   │   └── calibration.py            #   Calibración de severidad a partir de etiquetas
│   │
│   ├── llm/                           # Módulo transversal — LLM multi-proveedor
│   │   ├── __init__.py
│   │   ├── providers.py              #   Cliente unificado: OpenAI, GitHub Models, HF, Ollama
│   │   ├── prompts.py                #   Prompt templates para análisis contextual
│   │   └── analyzer.py               #   ContextualAnalyzer + RelevanceChecker
│   │
│   ├── alerts/                        # Módulo 7 — Motor de alertas
│   │   ├── engine.py                  #   Pipeline completo + LLM contextual + anti-spam
│   │   ├── deduplication.py           #   Deduplicación semántica 2 niveles (memoria + MongoDB con TTL)
│   │   └── explainer.py              #   Explicaciones LLM contextualizadas (+ template fallback)
│   │
│   ├── scheduler/                     # Módulo 8 — Scheduler automático
│   │   └── service.py                 #   APScheduler: ingesta cada 15min, alertas cada 20min, limpieza diaria
│   │
│   ├── notifications/                 # Módulo 9 — Notificaciones push
│   │   └── service.py                 #   Email SMTP (HTML) + Webhook HTTP (Slack/Discord/Telegram)
│   │
│   ├── advisor/                       # Módulo — Asesor de inversiones
│   │   ├── models.py                  #   Enums + modelos: RiskProfile, InvestorProfile, AdvisorReport
│   │   ├── questionnaire.py           #   10 preguntas MiFID + scoring ponderado
│   │   ├── analyzer.py                #   Análisis de cartera: HHI, concentración, diversificación
│   │   └── service.py                 #   Orquestación LLM (CFA/CAIA/CFP) + fallback determinista
│   │
│   ├── market/                        # Módulo 10 — Datos de mercado (yfinance)

│   │   └── service.py                 #   MarketService: lookup, precios, histórico OHLCV
│   │
│   ├── analytics/                     # Módulo 11 — Métricas de cartera (quantstats)

│   │   └── service.py                 #   AnalyticsService: Sharpe, Sortino, VaR, drawdown, alpha/beta
│   │
│   ├── backtest/                      # Módulo — Validación financiera + feedback
│   │   ├── event_study.py             #   Estudio de evento: AR/CAR (MacKinlay, 1997)
│   │   └── service.py                 #   Backtesting de alertas + autocalibración de umbrales
│   │
│   └── security/                      # Módulo — Capa de producción
│       ├── auth.py                    #   JWT + bcrypt + AuthService + get_current_user
│       ├── logging_config.py          #   structlog (logging estructurado JSON)
│       └── metrics.py                 #   Métricas Prometheus (HTTP + LLM)
│
├── tests/                             # Suite de tests (+200 tests, pytest)
│   ├── conftest.py                    #   Fixtures compartidos
│   ├── test_portfolio.py              #   Tests de modelos Portfolio/Asset
│   ├── test_nlp.py                    #   Tests de preprocesado y NER
│   ├── test_relevance.py              #   Tests de relevancia por cartera
│   ├── test_events.py                 #   Tests de clasificación de eventos
│   ├── test_impact.py                 #   Tests de estimación de impacto
│   ├── test_alerts.py                 #   Tests del motor de alertas
│   ├── test_llm.py                    #   Tests del cliente LLM
│   ├── test_ingestion.py              #   Tests de modelos de ingesta
│   ├── test_notifications.py          #   Tests de notificaciones
│   ├── test_scheduler.py              #   Tests del scheduler
│   ├── test_market.py                 #   Tests de datos de mercado (yfinance)
│   ├── test_analytics.py             #   Tests de métricas de cartera (quantstats)
│   ├── test_evaluation.py            #   Tests del marco de evaluación (métricas, IAA)
│   ├── test_agreement.py             #   Tests de acuerdo inter-anotador (κ, α)
│   ├── test_entity_resolver.py       #   Tests de resolución canónica de entidades
│   ├── test_calibration.py           #   Tests de calibración de severidad
│   ├── test_event_study.py           #   Tests de estudio de evento (AR/CAR)
│   ├── test_backtest.py              #   Tests de backtesting y feedback
│   └── test_security.py             #   Tests de auth, logging y métricas
│
└── pytest.ini                         # Configuración de pytest
```

---

## Requisitos Previos

| Requisito | Versión mínima | Notas |
|-----------|---------------|-------|
| Python | 3.11+ | Usa `list[str]` syntax (PEP 604) |
| MongoDB | 6.0+ | `docker run -d -p 27017:27017 --name mongo mongo:7` |
| RAM | 4 GB libres | FinBERT + embeddings + spaCy en memoria |
| Disco | ~2 GB | Modelos de Hugging Face (descarga automática al primer uso) |
| GPU | No requerida | Inferencia viable en CPU para el prototipo |

### API Keys opcionales

| Servicio | Para qué | Registro gratuito |
|----------|----------|-------------------|
| **GitHub Token** | LLM vía GitHub Models (Llama, Mistral, Phi — **recomendado**) | [github.com/settings/tokens](https://github.com/settings/tokens) |
| **HuggingFace Token** | LLM vía HF Inference API (alternativa gratuita) | [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) |
| **OpenAI** | LLM vía API de OpenAI (mayor calidad, de pago) | [platform.openai.com](https://platform.openai.com) |
| **NewsAPI** | Noticias con texto completo (100 req/día gratis) | [newsapi.org/register](https://newsapi.org/register) |
| **Alpha Vantage** | Noticias con tickers anotados (25 req/día gratis) | [alphavantage.co](https://www.alphavantage.co/support/#api-key) |

> Sin API keys el sistema funciona correctamente al 100%: usa zero-shot NLI local para
> clasificación de eventos, estimación de impacto determinista, y explicaciones con template.
> El LLM es un **enhancement layer** opcional que mejora la contextualización del impacto
> y las explicaciones, pero no es necesario para el funcionamiento básico.

---

## Instalación

```bash
# 1. Clonar / entrar al directorio
cd TFE

# 2. Crear entorno virtual
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux / Mac

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Descargar modelo spaCy (inglés)
python -m spacy download en_core_web_sm
# Para noticias en español (CNMV):
# python -m spacy download es_core_news_sm

# 5. Configurar variables de entorno
copy .env.example .env         # Windows
# cp .env.example .env         # Linux / Mac
# Editar .env con tus API keys (opcional)

# 6. Arrancar MongoDB
docker run -d -p 27017:27017 --name mongo mongo:7
# O si tienes MongoDB instalado localmente, asegúrate de que esté corriendo
```

---

## Ejecución

### Backend (API REST)

```bash
python main.py
```

- API: [http://localhost:8000](http://localhost:8000)
- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

Al arrancar, el **scheduler automático** comienza a ingestar noticias cada 15 minutos
y a procesar alertas para todas las carteras cada 20 minutos. Desactivable con
`SCHEDULER_ENABLED=false`.

### Frontend (Dashboard Next.js)

```bash
cd frontend
npm install
npm run dev
```

- Dashboard: [http://localhost:3000](http://localhost:3000)

> Backend y frontend deben estar corriendo simultáneamente (en terminales separadas).

### Docker (todo en un comando)

```bash
docker-compose up --build
```

Levanta los 3 servicios:
- **MongoDB** (mongo:7) en `localhost:27017`
- **API** (FastAPI) en `localhost:8000`
- **Frontend** (Next.js) en `localhost:3000`

Los modelos de Hugging Face se cachean en un volumen Docker (`huggingface_cache`)
para evitar re-descarga entre reinicios. El primer arranque tarda más (~2-5 min)
mientras se descargan los ~2.1 GB de modelos ML.

### Tests

```bash
pytest tests/ -v
```

+200 tests cubriendo todos los módulos del pipeline.

---

## Guía de Uso Paso a Paso

### 1. Crear una cartera

```bash
curl -X POST http://localhost:8000/api/portfolios \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "demo",
    "name": "Cartera Tech + IBEX",
    "assets": [
      {"ticker": "AAPL", "name": "Apple Inc.", "sector": "Technology", "country": "US", "weight": 0.25, "aliases": ["Apple"]},
      {"ticker": "MSFT", "name": "Microsoft Corp.", "sector": "Technology", "country": "US", "weight": 0.25, "aliases": ["Microsoft"]},
      {"ticker": "SAN.MC", "name": "Banco Santander", "sector": "Financials", "country": "ES", "weight": 0.20, "aliases": ["Santander"]},
      {"ticker": "ITX.MC", "name": "Inditex", "sector": "Consumer Discretionary", "country": "ES", "weight": 0.15, "aliases": ["Zara", "Inditex"]},
      {"ticker": "TSLA", "name": "Tesla Inc.", "sector": "Automotive", "country": "US", "weight": 0.15, "aliases": ["Tesla"]}
    ]
  }'
```

**Respuesta:**
```json
{"portfolio_id": "662f1a2b3c4d5e6f7a8b9c0d"}
```

### 2. Ingestar noticias

```bash
# Todas las fuentes
curl -X POST "http://localhost:8000/api/ingest?query=earnings"

# Solo RSS (22 feeds: finanzas, macro, cyber, supply chain, prensa ES)
curl -X POST http://localhost:8000/api/ingest/rss

# Solo CNMV (hechos relevantes + info privilegiada)
curl -X POST http://localhost:8000/api/ingest/cnmv

# NewsAPI (requiere NEWSAPI_KEY)
curl -X POST "http://localhost:8000/api/ingest/newsapi?query=Apple%20earnings&language=en"

# Alpha Vantage (requiere ALPHAVANTAGE_KEY)
curl -X POST "http://localhost:8000/api/ingest/alphavantage?tickers=AAPL,MSFT,TSLA"
```

### 3. Procesar noticias contra la cartera

```bash
# Procesar batch de noticias recientes
curl -X POST "http://localhost:8000/api/alerts/process-batch/662f1a2b3c4d5e6f7a8b9c0d?limit=50"
```

**Respuesta:**
```json
{"processed": 50, "alerts_generated": 7, "duplicates": 2, "discarded": 41}
```

### 4. Consultar alertas

```bash
curl "http://localhost:8000/api/alerts?portfolio_id=662f1a2b3c4d5e6f7a8b9c0d&limit=10"
```

### 5. Ejemplo de alerta generada

**Con LLM contextual (GitHub Models / HuggingFace / OpenAI):**
```
Apple enfrenta una demanda colectiva por prácticas monopolísticas en la App Store
que podría obligarle a abrir su ecosistema a tiendas de terceros. Esto afecta
directamente a tu posición en AAPL (25% de tu cartera) y podría reducir los
márgenes del segmento de servicios, que representa el 22% de los ingresos.
Confianza: 0.81. Fuente: reuters_business.
```

**Sin LLM (fallback con template):**
```
Posible alerta bajista de severidad alta para AAPL.
Evento detectado: Litigio / procedimiento legal.
Relevancia: mención directa de activo en cartera; sentimiento negative detectado por FinBERT.
Confianza: 0.81.
Fuente: reuters_business.
```

---

## Fuentes de Datos — 26 fuentes en 5 categorías

### Fuentes primarias regulatorias (sin API key)

| Fuente | Tipo | Cobertura | Contenido clave |
|--------|------|-----------|-----------------|
| **SEC EDGAR** | API REST | EE.UU. (todas las cotizadas) | 8-K (eventos materiales), 10-K, 10-Q |
| **CNMV** | RSS | España (BME) | Hechos relevantes, información privilegiada |

### Feeds RSS temáticos (sin API key)

| Categoría | Feeds | Cobertura de evento |
|-----------|-------|---------------------|
| **Finanzas generales** | Reuters, Yahoo Finance, FT, Seeking Alpha, Investing.com | Resultados, M&A, guidance, litigios |
| **Macroeconomía** | ECB, Fed, BoE, IMF | Tipos de interés, inflación, PIB |
| **Prensa española** | Expansión, Cinco Días, El Economista | Mercado español, IBEX 35 |
| **Ciberseguridad** | BleepingComputer, The Hacker News, SecurityWeek | Brechas de datos, ransomware |
| **Cadena de suministro** | Supply Chain Dive, FreightWaves | Logística, disrupciones, materias primas |

### APIs enriquecidas (requieren API key gratuita)

| Fuente | Ventaja diferencial | Límite gratuito |
|--------|---------------------|-----------------|
| **NewsAPI.org** | Texto completo + 150k fuentes globales | 100 req/día |
| **Alpha Vantage** | Tickers ya anotados + sentiment score por ticker | 25 req/día |

---

## Taxonomía de Eventos

El sistema clasifica cada noticia en una de **12 categorías** de evento financiero:

| Código | Evento | Ejemplos | Dirección típica |
|--------|--------|----------|:----------------:|
| `resultados_empresariales` | Earnings, EPS, revenue | Resultados Q4, beat/miss | Variable |
| `guidance_profit_warning` | Outlook, profit warning | Rebaja de guidance FY26 | ↓ Bajista |
| `regulacion` | Fines, sanctions, policy | Multa antimonopolio UE | ↓ Bajista |
| `litigio` | Lawsuits, investigations | Class action, investigación SEC | ↓ Bajista |
| `fusion_adquisicion` | M&A, takeovers, JVs | OPA sobre compañía X | Variable |
| `ciberincidente` | Data breach, ransomware | Filtración de datos de clientes | ↓↓ Muy bajista |
| `incidencia_operativa` | Outages, recalls | Recall de producto masivo | ↓ Bajista |
| `macroeconomia` | Interest rates, inflation | Subida de tipos del BCE | Variable |
| `cadena_suministro` | Logistics, shortages | Escasez de semiconductores | ↓ Bajista |
| `cambio_directivo` | CEO, board changes | Dimisión inesperada del CEO | Variable |
| `dividendo_recompra` | Dividends, buybacks | Recompra de acciones $10B | ↑ Alcista |
| `otro` | Uncategorized | — | Neutral |

---

## Endpoints de la API

### Portfolio

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/api/portfolios` | Crear cartera |
| `GET` | `/api/portfolios?user_id=X` | Listar carteras de un usuario |
| `GET` | `/api/portfolios/{id}` | Obtener una cartera |
| `POST` | `/api/portfolios/{id}/assets` | Añadir activo |
| `DELETE` | `/api/portfolios/{id}/assets/{ticker}` | Eliminar activo |

### Ingestion

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/api/ingest` | Ingesta completa (todas las fuentes) |
| `POST` | `/api/ingest/rss` | Solo RSS (22 feeds) |
| `POST` | `/api/ingest/cnmv` | Solo CNMV |
| `POST` | `/api/ingest/newsapi?query=X` | NewsAPI (requiere key) |
| `POST` | `/api/ingest/alphavantage?tickers=X` | Alpha Vantage (requiere key) |
| `GET` | `/api/news?limit=N` | Noticias recientes almacenadas |

### Alerts

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/api/alerts/process` | Procesar una noticia individual |
| `POST` | `/api/alerts/process-batch/{portfolio_id}` | Procesar batch contra cartera |
| `GET` | `/api/alerts?portfolio_id=X&limit=N` | Listar alertas |
| `GET` | `/api/alerts/stats?portfolio_id=X` | Estadísticas agregadas |

### Advisor

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/api/advisor/questions` | Cuestionario MiFID (10 preguntas) |
| `POST` | `/api/advisor/profile` | Calcular perfil de inversor |
| `POST` | `/api/advisor/report` | Generar informe de asesoramiento |
| `GET` | `/api/advisor/reports/{portfolio_id}` | Historial de informes |

### Market Data

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/api/market/lookup/{ticker}` | Auto-fill: busca info de un activo |
| `GET` | `/api/market/price/{ticker}` | Precio actual + variación diaria |
| `POST` | `/api/market/prices` | Precios en lote |
| `GET` | `/api/market/history/{ticker}?period=1y` | Histórico OHLCV |

### Analytics

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/api/analytics/{portfolio_id}?period=1y&benchmark=SPY` | Métricas completas de cartera |

### Backtesting y validación financiera

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/api/backtest/{portfolio_id}` | Estudio de evento (AR/CAR) + métricas de backtest de las alertas |
| `POST` | `/api/backtest/{portfolio_id}/calibrate` | Recalibrar umbrales a partir del feedback acumulado |

### Autenticación (capa de producción)

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/api/auth/register` | Registrar usuario (JWT + bcrypt) |
| `POST` | `/api/auth/login` | Obtener token de acceso |
| `GET` | `/api/auth/me` | Datos del usuario autenticado |

> La autenticación se controla con `AUTH_ENABLED` (por defecto `false` para desarrollo).

### Sistema y observabilidad

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/api/system/status` | Estado del scheduler, próximas ejecuciones, notificaciones |
| `GET` | `/metrics` | Métricas en formato Prometheus (HTTP + LLM) |
| `GET` | `/health/live` | Liveness probe |
| `GET` | `/health/ready` | Readiness probe |
| `GET` | `/health/db` | Comprobación de conexión a MongoDB |

---

## Evaluación

El sistema se evalúa en **tres planos** complementarios. Los resultados completos
están en `evaluation/results/` y se reproducen con `python -m evaluation.run_ablation`.

### Plano 1 — Fiabilidad del corpus (acuerdo inter-anotador)

Doble anotación independiente sobre el corpus de evaluación (`evaluation/agreement.py`):

| Dimensión | Métrica | Valor | Interpretación (Landis y Koch, 1977) |
|-----------|---------|:-----:|--------------------------------------|
| Relevancia | κ de Cohen | 0,86 | Casi perfecto |
| Tipo de evento | κ de Cohen | 1,00 | Perfecto |
| Dirección | κ de Cohen | 0,88 | Casi perfecto |
| Severidad | κ ponderado (cuadrático) | 0,82 | Casi perfecto |
| Severidad (ordinal) | α de Krippendorff | 0,91 | Casi perfecto |

> **Nota metodológica**: el acuerdo exacto en severidad es bajo (0,56) por ser la
> dimensión más subjetiva, pero los desacuerdos son casi siempre entre categorías
> adyacentes (alta vs muy_alta). Por eso se reportan κ ponderado y α ordinal, que
> penalizan menos los desacuerdos cercanos. Escala de interpretación: Landis y
> Koch (1977).

### Plano 2 — Calidad predictiva (estudio de ablación)

Cuatro variantes del pipeline (`evaluation/results/ablation_summary.json`):

| Variante | Relevancia F1 | Evento F1 macro | Dirección Acc | Severidad MAE | Severidad ±1 |
|----------|:-------------:|:---------------:|:-------------:|:-------------:|:------------:|
| `rules` (solo reglas) | 0,935 | — | — | — | — |
| `hybrid` (reglas + semántica) | 0,900 | — | — | — | — |
| `hybrid_nli` (+ NLI zero-shot) | 0,900 | 0,735 | 0,926 | 0,593 | 0,889 |
| `full` (+ LLM contextual) | 0,935 | 0,893 | 0,931 | 0,621 | 1,000 |

### Plano 3 — Validez financiera (estudio de evento)

Estudio de evento sobre las alertas (`modules/backtest/event_study.py`, MacKinlay 1997):

| Métrica | Descripción |
|---------|-------------|
| **CAR** (Cumulative Abnormal Return) | Retorno anormal acumulado en ventana [-1, +3] días tras la alerta |
| **AR** (Abnormal Return) | Retorno diario respecto al modelo de mercado estimado |
| **Tasa de falsos positivos** | % de alertas sin movimiento anormal real del activo |
| **Backtesting + feedback** | Autocalibración de umbrales vía `/api/backtest/{id}/calibrate` |

---

## Variables de Entorno

| Variable | Obligatoria | Default | Descripción |
|----------|:-----------:|---------|-------------|
| `MONGO_URI` | Sí | `mongodb://localhost:27017` | Conexión a MongoDB |
| `MONGO_DB_NAME` | No | `portfolio_alerts` | Nombre de la base de datos |
| `SEC_USER_AGENT` | Sí* | — | *La SEC exige nombre + email real* |
| `LLM_PROVIDER` | No | `github` | Proveedor LLM: `github`, `huggingface`, `openai`, `ollama` |
| `LLM_MODEL` | No | (default del proveedor) | Modelo LLM a usar (ej: `meta-llama-3.1-8b-instruct`) |
| `LLM_BASE_URL` | No | (auto por proveedor) | Base URL custom del proveedor |
| `LLM_API_KEY` | No | — | API key directa (alternativa a variables por proveedor) |
| `GITHUB_TOKEN` | No | — | Token de GitHub para GitHub Models |
| `HF_TOKEN` | No | — | Token de HuggingFace para Inference API |
| `OPENAI_API_KEY` | No | — | API key de OpenAI |
| `NLI_MODEL` | No | `facebook/bart-large-mnli` | Modelo zero-shot NLI para clasificar eventos |
| `NEWSAPI_KEY` | No | — | Noticias con texto completo |
| `ALPHAVANTAGE_KEY` | No | — | Noticias con tickers anotados |
| `FINBERT_MODEL` | No | `ProsusAI/finbert` | Modelo de sentiment |
| `EMBEDDING_MODEL` | No | `sentence-transformers/all-MiniLM-L6-v2` | Embeddings semánticos |
| `SPACY_MODEL` | No | `en_core_web_sm` | Modelo NER de spaCy |
| `SCHEDULER_ENABLED` | No | `true` | Activar/desactivar scheduler automático |
| `SCHEDULER_INGEST_INTERVAL_MIN` | No | `15` | Intervalo de ingesta RSS+CNMV (minutos) |
| `SCHEDULER_ALERTS_INTERVAL_MIN` | No | `20` | Intervalo de procesamiento de alertas (minutos) |
| `SCHEDULER_BATCH_SIZE` | No | `50` | Noticias por batch de alertas |
| `SCHEDULER_NEWS_RETENTION_DAYS` | No | `30` | Retención de noticias antiguas (días) |
| `NOTIFICATIONS_ENABLED` | No | `true` | Activar/desactivar notificaciones |
| `SMTP_HOST` | No | — | Servidor SMTP (ej: `smtp.gmail.com`) |
| `SMTP_PORT` | No | `587` | Puerto SMTP |
| `SMTP_USE_TLS` | No | `true` | Usar TLS para SMTP |
| `SMTP_USER` | No | — | Usuario SMTP |
| `SMTP_PASSWORD` | No | — | Contraseña SMTP |
| `SMTP_FROM` | No | — | Dirección remitente de emails |
| `NOTIFICATION_EMAIL_TO` | No | — | Emails destinatarios (separados por coma) |
| `NOTIFICATION_WEBHOOK_URL` | No | — | URL webhook (Slack/Discord/Telegram/custom) |
| `AUTH_ENABLED` | No | `false` | Activar autenticación JWT en los endpoints |
| `JWT_SECRET` | Sí** | `dev-insecure-secret-change-me` | **Cámbiala en producción**. Clave de firma HS256 |
| `JWT_ALGORITHM` | No | `HS256` | Algoritmo de firma del token |
| `JWT_EXPIRE_MINUTES` | No | `1440` | Caducidad del token de acceso (minutos, 24 h) |
| `CORS_ORIGINS` | No | `*` | Orígenes permitidos para CORS (separados por coma) |
| `RATE_LIMIT_ENABLED` | No | `true` | Activar/desactivar el rate limiting |
| `RATE_LIMIT_DEFAULT` | No | `120/minute` | Límite por defecto de peticiones |
| `RATE_LIMIT_AUTH` | No | `10/minute` | Límite específico para endpoints de autenticación |

---

## Reproducibilidad de la evaluación

```bash
# Estudio de ablación completo (rules → hybrid → hybrid_nli → full)
python -m evaluation.run_ablation

# Solo variantes concretas
python -m evaluation.run_ablation --variants rules hybrid

# Acuerdo inter-anotador (κ de Cohen, α de Krippendorff)
python -m evaluation.run_agreement

# Tests del marco de evaluación
pytest tests/test_evaluation.py tests/test_agreement.py -v
```

- Corpus: `evaluation/dataset.jsonl` (40 noticias, 3 carteras, 21 EN + 19 ES,
  los 12 tipos de evento cubiertos, 5 negativos deliberados y hard cases de
  relevancia indirecta como TSMC→AAPL o algodón→Inditex).
- Doble anotación independiente de 25 ítems en `evaluation/dataset_annotator2.jsonl`.
- Resultados en `evaluation/results/` (`<variante>_predictions.jsonl`,
  `<variante>_metrics.json`, `ablation_summary.json`, `agreement.json`).
- **Metodología train/test**: los modelos (FinBERT, BART-MNLI, embeddings) se
  usan preentrenados/zero-shot, sin fine-tuning, y las reglas se definieron a
  priori; el corpus completo actúa como conjunto de test no visto, por lo que
  no existe contaminación entre entrenamiento y evaluación.
- Las variantes `hybrid_nli` y `full` cargan FinBERT + BART-MNLI +
  sentence-transformers (~3 GB RAM, minutos por variante en CPU). `full` cae
  automáticamente a `hybrid_nli` si no hay API key de LLM configurada.

### Esquema de etiquetado

```json
{
  "id": "ev001",
  "portfolio_id": "tech_us",
  "title": "...", "summary": "...", "content": "...",
  "labels": {
    "is_relevant": true,
    "matched_assets": ["AAPL"],
    "event_type": "resultados_empresariales",
    "direction": "alcista",
    "severity_label": "alta"
  }
}
```

---

## Base de datos (MongoDB)

Capa async sobre MongoDB con **Motor** (`database/mongodb.py`, clase `MongoDB`:
`connect()`/`close()` + helpers `insert_one`/`find`).

| Colección | Contenido | Índices (creados en `connect()`) |
|-----------|-----------|----------------------------------|
| `portfolios` | Carteras (activos, sectores, pesos) | — |
| `news` | Noticias ingestadas | `url` (unique), text index `title`+`summary`, `published_at` desc |
| `alerts` | Alertas generadas | `portfolio_id`, `created_at` desc |
| `events` | Eventos clasificados (auditoría) | `created_at` desc |

Configuración vía `MONGO_URI` (default `mongodb://localhost:27017`) y
`MONGO_DB_NAME` (default `portfolio_alerts`).

---

## Licencia

Proyecto académico — Trabajo Fin de Máster, UNIR 2026.
