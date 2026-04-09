# Sistema de Alertas Inteligentes por Noticias para Carteras de Inversión

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
                                                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            5. CLASIFICACIÓN DE EVENTOS                          │
│  FinBERT (sentiment) + LLM / keyword fallback (tipo de evento × taxonomía)     │
└──────────────────────────────────────┬──────────────────────────────────────────┘
                                       │
                                       ▼
┌──────────────────┐    ┌──────────────────────────────────────────────────────┐
│  6. ESTIMACIÓN   │───▸│  7. MOTOR DE ALERTAS                                │
│  DE IMPACTO      │    │  Score compuesto · Deduplicación semántica ·        │
│  Dirección ·     │    │  Anti-spam · Generación de explicación trazable     │
│  Severidad ·     │    └──────────────────────────────────────────────────────┘
│  Confianza       │
└──────────────────┘
```

Cada módulo tiene su propia documentación detallada en `modules/<módulo>/README.md`.

---

## Stack Tecnológico

| Capa | Tecnología | Rol |
|------|-----------|-----|
| **API** | FastAPI + Uvicorn | Backend REST asíncrono |
| **Frontend** | Streamlit | Dashboard interactivo para gestión y visualización |
| **Base de datos** | MongoDB (Motor async) | Almacenamiento de noticias, carteras y alertas |
| **Sentiment** | FinBERT (`ProsusAI/finbert`) | Análisis de sentimiento financiero |
| **Embeddings** | Sentence-Transformers (`all-MiniLM-L6-v2`) | Similitud semántica y deduplicación |
| **NER** | spaCy (`en_core_web_sm`) | Reconocimiento de entidades nombradas |
| **Clasificación** | OpenAI API (`gpt-4o-mini`) + fallback keywords | Tipo de evento financiero |
| **Ingesta** | feedparser + httpx | RSS, SEC EDGAR, CNMV, NewsAPI, Alpha Vantage |

---

## Estructura del Proyecto

```
TFE/
│
├── config.py                          # Configuración central (modelos, fuentes, umbrales)
├── main.py                            # API REST (FastAPI) — punto de entrada del backend
├── app.py                             # Dashboard (Streamlit) — interfaz de usuario
├── requirements.txt                   # Dependencias Python
├── .env.example                       # Template de variables de entorno
│
├── database/
│   ├── __init__.py
│   └── mongodb.py                     # Conexión async, colecciones, índices
│
├── modules/
│   ├── portfolio/                     # Módulo 1 — Modelado de cartera
│   │   ├── README.md
│   │   ├── models.py                  #   Schemas: Asset, Portfolio
│   │   └── service.py                 #   CRUD sobre MongoDB
│   │
│   ├── ingestion/                     # Módulo 2 — Adquisición de noticias
│   │   ├── README.md
│   │   ├── models.py                  #   Schema: NewsItem
│   │   ├── rss_feeds.py              #   22 feeds RSS (finanzas, macro, cyber, supply chain)
│   │   ├── sec_edgar.py              #   SEC EDGAR API (8-K, 10-K, 10-Q)
│   │   ├── cnmv.py                   #   CNMV RSS (hechos relevantes, info privilegiada)
│   │   ├── newsapi.py                #   NewsAPI.org (texto completo, +150k fuentes)
│   │   ├── alphavantage.py           #   Alpha Vantage (tickers anotados + sentimiento)
│   │   └── service.py                #   Orquestador: ingesta + dedup por hash + persistencia
│   │
│   ├── nlp/                           # Módulo 3 — Preprocesado NLP
│   │   ├── README.md
│   │   └── preprocessing.py          #   Limpieza, NER, detección de idioma
│   │
│   ├── relevance/                     # Módulo 4 — Relevancia por cartera
│   │   ├── README.md
│   │   └── service.py                #   Reglas explícitas + similitud semántica
│   │
│   ├── events/                        # Módulo 5 — Clasificación de eventos
│   │   ├── README.md
│   │   └── classifier.py             #   FinBERT + LLM/keyword fallback
│   │
│   ├── impact/                        # Módulo 6 — Estimación de impacto
│   │   ├── README.md
│   │   └── estimator.py              #   Dirección, severidad, confianza
│   │
│   └── alerts/                        # Módulo 7 — Motor de alertas
│       ├── README.md
│       ├── engine.py                  #   Pipeline completo + anti-spam
│       ├── deduplication.py           #   Deduplicación semántica con embeddings
│       └── explainer.py              #   Generación de explicaciones en lenguaje natural
│
├── NOTAS_TECNICAS.md                  # Pendientes, mejoras, decisiones de diseño
├── TFM_alertas_inversion_estado_de_la_cuestion.pdf
└── TFM_alertas_inversion_estado_de_la_cuestion.docx
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
| **OpenAI** | Clasificación avanzada de eventos | [platform.openai.com](https://platform.openai.com) |
| **NewsAPI** | Noticias con texto completo (100 req/día gratis) | [newsapi.org/register](https://newsapi.org/register) |
| **Alpha Vantage** | Noticias con tickers anotados (25 req/día gratis) | [alphavantage.co](https://www.alphavantage.co/support/#api-key) |

> Sin API keys el sistema funciona correctamente: usa fallback por keywords para eventos
> y se limita a las fuentes RSS + SEC EDGAR + CNMV (que no requieren autenticación).

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

### Frontend (Dashboard)

```bash
streamlit run app.py
```

- Dashboard: [http://localhost:8501](http://localhost:8501)

> Ambos deben estar corriendo simultáneamente (en terminales separadas).

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

---

## Evaluación Prevista

El sistema se evalúa en **dos planos** independientes:

### Plano NLP (por módulo)

| Métrica | Módulo evaluado | Propósito |
|---------|----------------|-----------|
| Precision, Recall, F1 | Clasificación de eventos | ¿Clasifica correctamente el tipo de evento? |
| Accuracy | Sentiment (FinBERT) | ¿Detecta correctamente la polaridad? |
| Calibración (Platt / isotonic) | Score de confianza | ¿El 0.8 de confianza real = 80% acierto? |
| Confusion matrix | Evento + dirección | ¿Dónde se equivoca más? |

### Plano Financiero (utilidad de la señal)

| Métrica | Descripción |
|---------|-------------|
| **CAR** (Cumulative Abnormal Return) | Retorno anormal acumulado en ventana [-1, +3] días tras la alerta |
| **Comparación vs. baselines** | Baseline 1: solo keywords · Baseline 2: solo FinBERT · Baseline 3: sistema completo |
| **Tasa de falsos positivos** | % de alertas sin movimiento real del activo |
| **Tasa de cobertura** | % de eventos reales detectados por el sistema |

---

## Variables de Entorno

| Variable | Obligatoria | Default | Descripción |
|----------|:-----------:|---------|-------------|
| `MONGO_URI` | Sí | `mongodb://localhost:27017` | Conexión a MongoDB |
| `MONGO_DB_NAME` | No | `portfolio_alerts` | Nombre de la base de datos |
| `SEC_USER_AGENT` | Sí* | — | *La SEC exige nombre + email real* |
| `OPENAI_API_KEY` | No | — | Clasificación avanzada de eventos |
| `OPENAI_MODEL` | No | `gpt-4o-mini` | Modelo de OpenAI a utilizar |
| `NEWSAPI_KEY` | No | — | Noticias con texto completo |
| `ALPHAVANTAGE_KEY` | No | — | Noticias con tickers anotados |
| `FINBERT_MODEL` | No | `ProsusAI/finbert` | Modelo de sentiment |
| `EMBEDDING_MODEL` | No | `sentence-transformers/all-MiniLM-L6-v2` | Embeddings semánticos |
| `SPACY_MODEL` | No | `en_core_web_sm` | Modelo NER de spaCy |

---

## Documentación Adicional

| Documento | Contenido |
|-----------|-----------|
| [`NOTAS_TECNICAS.md`](NOTAS_TECNICAS.md) | Pendientes, posibles mejoras, selección de modelos, detalle de fuentes |
| [`modules/portfolio/README.md`](modules/portfolio/README.md) | Módulo 1 — Modelado de cartera |
| [`modules/ingestion/README.md`](modules/ingestion/README.md) | Módulo 2 — Adquisición de noticias |
| [`modules/nlp/README.md`](modules/nlp/README.md) | Módulo 3 — Preprocesado NLP |
| [`modules/relevance/README.md`](modules/relevance/README.md) | Módulo 4 — Relevancia por cartera |
| [`modules/events/README.md`](modules/events/README.md) | Módulo 5 — Clasificación de eventos |
| [`modules/impact/README.md`](modules/impact/README.md) | Módulo 6 — Estimación de impacto |
| [`modules/alerts/README.md`](modules/alerts/README.md) | Módulo 7 — Motor de alertas |

---

## Licencia

Proyecto académico — Trabajo Fin de Máster, UNIR 2026.
