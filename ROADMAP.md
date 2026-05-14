# ROADMAP — De Prototipo Académico a Sistema Profesional

> Estado actual: **prototipo funcional con pipeline NLP completo, scheduler automático,
> notificaciones, suite de tests (95 tests), Docker/docker-compose y todas las mejoras
> de Tier 2 implementadas** (async I/O, entity matching, dedup persistente, cold start,
> traducción ES→EN). Faltan autenticación y capas de producción avanzadas.

---

## Resumen Ejecutivo

| Dimensión | Hoy | Objetivo producción |
|-----------|:---:|:-------------------:|
| Pipeline NLP | ✅ Completo | ✅ |
| Ingesta automática | ✅ Scheduler cada 15 min | ✅ |
| Notificaciones | ✅ Email + Webhook | ✅ |
| Tests | ✅ 95 tests (pytest) | ~300+ tests |
| I/O async | ✅ feedparser + AsyncOpenAI | ✅ |
| Entity matching | ✅ Word-boundary regex | ✅ |
| Dedup persistente | ✅ Memoria + MongoDB TTL | ✅ |
| Cold start preload | ✅ Lifespan ThreadPool | ✅ |
| Traducción ES→EN | ✅ deep-translator | ✅ |
| Containerización | ✅ Docker + docker-compose | ✅ |
| Autenticación | ❌ Ninguna | JWT + multi-tenant |
| Monitorización | ❌ Ninguna | Structured logging + APM |
| Escalabilidad | ❌ Single worker | Task queue + multi-worker |

---

## TIER 1 — Deal-breakers (sin esto nadie lo usa)

### 1.1 ✅ Ingesta automática — COMPLETADO

- **Qué se hizo:** Módulo `modules/scheduler/` con APScheduler integrado en el event loop de FastAPI.
- **Jobs configurados:**
  - Ingesta RSS + CNMV cada 15 min (`SCHEDULER_INGEST_INTERVAL_MIN`)
  - Procesamiento batch de alertas para todas las carteras cada 20 min (`SCHEDULER_ALERTS_INTERVAL_MIN`)
  - Limpieza de noticias antiguas (>30 días) cada 24h
- **Endpoint:** `GET /api/system/status` devuelve estado del scheduler y próximas ejecuciones.
- **Configuración:** Todo via env vars, desactivable con `SCHEDULER_ENABLED=false`.

### 1.2 ✅ Notificaciones push — COMPLETADO

- **Qué se hizo:** Módulo `modules/notifications/` con dos canales:
  - **Email** vía SMTP (compatible Gmail, Outlook, SendGrid, Resend). HTML profesional + plaintext.
  - **Webhook** HTTP POST (compatible Slack, Discord, Telegram bots, endpoints custom).
- **Integración:** Se dispara automáticamente en `AlertEngine.process_and_store()`.
- **Configuración:** Env vars `SMTP_HOST`, `SMTP_FROM`, `NOTIFICATION_EMAIL_TO`, `NOTIFICATION_WEBHOOK_URL`.
- **Degradación elegante:** Si no están configurados, el sistema funciona sin notificaciones.

### 1.3 ✅ Suite de tests — COMPLETADO

- **95 tests** en 9 archivos, todos pasando.
- Cobertura por módulo:

| Archivo | Tests | Módulo |
|---------|:-----:|--------|
| `test_portfolio.py` | 9 | Models: Asset, Portfolio, getters |
| `test_nlp.py` | 11 | Limpieza HTML/URLs, NER, detección idioma |
| `test_relevance.py` | 9 | Matching directo, NER, sector, semántico |
| `test_events.py` | 11 | FinBERT sentiment, zero-shot NLI, fallback keywords |
| `test_impact.py` | 11 | Estimación determinista, merge LLM, severity labels |
| `test_alerts.py` | 13 | Cosine similarity, deduplicación, explainer (LLM + template) |
| `test_llm.py` | 14 | Providers config, JSON parsing, clamp, format portfolio |
| `test_ingestion.py` | 3 | NewsItem model |
| `test_notifications.py` | 8 | Email, webhook, formatters, status |
| `test_scheduler.py` | 1 | Scheduler status |

### 1.4 ❌ Autenticación — PENDIENTE

**Qué falta:**

El sistema actual no tiene ninguna capa de autenticación. Cualquiera con acceso de red
puede crear/leer/borrar carteras, disparar ingestas y ver alertas de cualquier usuario.
CORS está en `allow_origins=["*"]`.

**Plan de implementación:**

#### Opción A: JWT + FastAPI (recomendada para TFM)

```
Complejidad: Media
Dependencias: python-jose[cryptography], passlib[bcrypt]
Tiempo estimado: 1-2 días
```

1. **Nueva colección MongoDB** `users` con campos: `email`, `password_hash`, `created_at`, `is_active`.
2. **Endpoints de auth:**
   - `POST /api/auth/register` — registro con email + contraseña (hash bcrypt).
   - `POST /api/auth/login` — devuelve JWT (access token + refresh token).
   - `POST /api/auth/refresh` — renueva access token.
3. **Middleware de autenticación:**
   - Extraer JWT del header `Authorization: Bearer <token>`.
   - Validar firma, expiración, y extraer `user_id`.
   - Inyectar `user_id` en el request state.
4. **Filtrado por usuario:**
   - Todas las queries a `portfolios` filtran por `user_id` del token.
   - Las alertas se filtran por `portfolio_id` que pertenezca al usuario.
   - Endpoint de ingesta: solo el scheduler o admins (no usuarios normales).
5. **CORS restringido:**
   - Cambiar `allow_origins=["*"]` por la URL del frontend desplegado.
6. **Frontend:**
   - Pantalla de login/registro en Next.js.
   - Guardar JWT en `httpOnly` cookie o `localStorage`.
   - Interceptor en `api.ts` que añade `Authorization` header.

#### Opción B: NextAuth.js + API keys (más rápida)

```
Complejidad: Baja
Tiempo estimado: 1 día
```

1. NextAuth.js en el frontend con provider de credenciales o GitHub OAuth.
2. API key generada por usuario almacenada en MongoDB.
3. FastAPI valida la API key en cada request.
4. Menos seguro que JWT pero más rápido de implementar.

#### Opción C: Clerk / Auth0 (SaaS)

```
Complejidad: Muy baja
Tiempo estimado: Medio día
Coste: Gratuito hasta 10k MAU (Clerk) o 7k MAU (Auth0)
```

1. Integrar Clerk o Auth0 como proveedor de identidad.
2. Frontend usa SDK de Clerk/Auth0.
3. Backend valida JWT emitido por Clerk/Auth0.
4. Sin gestión de contraseñas propia.

**Recomendación:** Para el TFM, **Opción A** (JWT propio) demuestra más competencia técnica.
Para un producto real, **Opción C** (Clerk/Auth0) es más segura y rápida.

---

## TIER 2 — "Funciona en la demo pero no en real"

### 2.1 ✅ Fix I/O bloqueante en async — COMPLETADO

**Problema:** `feedparser` (sync) y `openai` SDK (sync) se ejecutaban dentro del event loop
async de FastAPI. Con 22 feeds RSS, la API se congelaba ~10-30s por ingesta.

**Solución implementada:**

- **RSS/CNMV:** `fetch_rss_feed` y `fetch_cnmv_feed` envueltos en `asyncio.run_in_executor()`. `fetch_all_rss()` y `fetch_all_cnmv()` usan `asyncio.gather()` para descarga paralela de todos los feeds.
- **LLM:** `openai.OpenAI` reemplazado por `openai.AsyncOpenAI`. `LLMClient.chat()` es ahora `async def` con `await client.chat.completions.create()`.
- **Callers actualizados:** `ContextualAnalyzer.analyze()`, `RelevanceChecker.check()`, `AlertEngine.process_news()` y el scheduler usan `await` correctamente.

### 2.2 ✅ Deduplicación persistente — COMPLETADO

**Problema:** El `SemanticDeduplicator` mantenía un buffer de 200 embeddings **en memoria**.
Se perdía al reiniciar el proceso. Resultado: después de cada deploy, las mismas noticias
generaban alertas duplicadas.

**Solución implementada:**

- Deduplicación a **2 niveles**: caché en memoria (200 últimos, rápido) + MongoDB persistente (500 últimos, con TTL de 30 días).
- Nueva colección `dedup_embeddings` con índice TTL (`expireAfterSeconds=30*24*3600`) e índice por `alert_id`.
- `is_duplicate()` es ahora `async def`: primero busca en memoria, si no hay match busca en MongoDB.
- Al encontrar no-duplicado, guarda en ambos niveles simultáneamente.

### 2.3 ✅ Fix entity matching — COMPLETADO

**Problema:** El matching de tickers usaba `if name in text_lower`, causando falsos
positivos masivos con tickers cortos: `"US"` matcheaba con "bec**us**e", "disc**us**s".

**Solución implementada:**

- Función `_is_name_match()` con `re.search(r'\b...\b', text)` para word-boundary matching.
- Set `_COMMON_WORDS` con palabras comunes en inglés (“a”, “it”, “ai”, “us”, “or”, “all”) que usan word-boundary aún si son >3 caracteres.
- Aplicado tanto a nombres de empresas como a países en `RuleBasedRelevance.compute()`.

### 2.4 ✅ Modelos solo inglés + fuentes en español — COMPLETADO

**Problema:** CNMV publica en español. FinBERT y BART-MNLI solo entienden inglés.
El sentimiento y la clasificación de eventos eran incorrectos para esas noticias.

**Solución implementada:**

- Método `_translate_to_en()` en `NLPService` usando `deep_translator.GoogleTranslator(source="es", target="en")` con límite de 5000 caracteres.
- `NLPService.process()` detecta el idioma y, si es español, traduce automáticamente.
- El resultado incluye nuevo campo `cleaned_text_en` que se pasa al clasificador de eventos.
- `AlertEngine` usa `cleaned_text_en` para `event_service.classify()`, garantizando que FinBERT y BART-MNLI reciben texto en inglés.

### 2.5 ✅ Cold start de modelos — COMPLETADO

**Problema:** 4 modelos ML (~2.1 GB) se cargaban en la primera request. El usuario veía un timeout
de ~30-60 segundos.

**Solución implementada:**

- Función `_preload_models()` en `main.py` que carga spaCy, FinBERT, BART-MNLI y sentence-transformers.
- Se ejecuta en el `lifespan` de FastAPI dentro de un `ThreadPoolExecutor(max_workers=1)` via `loop.run_in_executor()`, antes de aceptar requests.
- El `AlertEngine` se inicializa después del preload, garantizando que todos los modelos estén disponibles.

---

## TIER 3 — Producto competitivo (cobrar por ello)

### 3.1 ❌ WebSocket/SSE para alertas en tiempo real — PENDIENTE

**Qué:** El frontend actualmente solo ve alertas cuando el usuario recarga la página o
pulsa un botón. Un sistema de alertas real necesita notificaciones push in-app.

**Implementación:**

```python
# FastAPI SSE endpoint
from sse_starlette.sse import EventSourceResponse

@app.get("/api/alerts/stream/{portfolio_id}")
async def alert_stream(portfolio_id: str):
    async def event_generator():
        # Listener en MongoDB Change Streams
        async with MongoDB.alerts().watch([
            {"$match": {"fullDocument.portfolio_id": portfolio_id}}
        ]) as stream:
            async for change in stream:
                yield {"data": json.dumps(change["fullDocument"])}
    return EventSourceResponse(event_generator())
```

En el frontend: `EventSource` nativo o `useEffect` con SSE para recibir alertas en vivo.

### 3.2 ❌ Historial de alertas con analytics — PENDIENTE

**Qué:** Tracking de si las alertas fueron útiles. Datos para mejorar el sistema.

- Botones "✅ Útil / ❌ No útil" en cada alerta.
- Dashboard de accuracy histórica: % de alertas marcadas como útiles.
- Correlación con movimiento real del precio (backtesting).
- Permitir exportar alertas a CSV.

### 3.3 ❌ Backtesting — PENDIENTE

**Qué:** ¿La alerta acertó? Comparar la dirección predicha con el movimiento real del precio.

**Implementación:**

1. Cuando se genera una alerta, registrar los tickers afectados y el precio actual.
2. Pasados N días (configurable, ej: 3), consultar el precio actual de esos tickers.
3. Calcular retorno real y comparar con la dirección predicha.
4. Métricas: hit rate, CAR (Cumulative Abnormal Return), Sharpe ratio de la señal.
5. Fuente de precios: Yahoo Finance (`yfinance`) o Alpha Vantage.

### 3.4 ❌ Rate limiting en la API — PENDIENTE

**Qué:** El anti-spam existe solo en el alert engine (20/hora). La API HTTP no tiene
rate limiting — un cliente malicioso puede hacer miles de requests.

**Implementación:** `slowapi` (wrapper de `limits` para FastAPI).

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/api/ingest")
@limiter.limit("10/minute")
async def ingest_all(request: Request, ...):
    ...
```

### 3.5 ❌ Monitorización y logging estructurado — PENDIENTE

**Qué:** Sin observabilidad, los errores en producción pasan desapercibidos.

**Plan:**

1. **Logging estructurado** con `structlog` o `python-json-logger` (formato JSON).
2. **Sentry** para captura automática de excepciones con contexto.
3. **Métricas Prometheus** via `prometheus-fastapi-instrumentator`:
   - Latencia por endpoint
   - Alertas generadas/hora
   - Modelos NLP: tiempo de inferencia
   - LLM: tokens consumidos, latencia, errores
4. **Dashboard Grafana** conectado a Prometheus.
5. **Health checks** extendidos: `/health/ready` (modelos cargados), `/health/live` (API responde),
   `/health/db` (MongoDB conectado).

### 3.6 ✅ Docker + CI/CD — COMPLETADO (Docker)

**Qué se hizo:**

- **`Dockerfile`** (backend): Multi-stage build (builder con build-essential + runtime con python:3.13-slim). Instala spaCy model. Healthcheck en `/api/system/status` con 120s start period.
- **`frontend/Dockerfile`**: Node 22 Alpine, standalone Next.js build. Acepta `NEXT_PUBLIC_API_BASE_URL` como build arg.
- **`docker-compose.yml`**: 3 servicios (MongoDB 7, API FastAPI, Frontend Next.js). Volumen para caché de modelos HuggingFace. Healthcheck en MongoDB antes de arrancar API.
- **`.dockerignore`**: Exclusiones para __pycache__, .venv, .env, node_modules, .next, tests.
- **`next.config.ts`**: Añadido `output: "standalone"` para builds Docker optimizados.
- **`main.py`**: `reload` controlado por env var `UVICORN_RELOAD` (desactivado en Docker por defecto).

**Pendiente:** CI/CD con GitHub Actions (`test.yml` + `deploy.yml`).

**`docker-compose up --build`** levanta todo el stack en un solo comando.

### 3.7 ❌ Task queue para procesamiento async — PENDIENTE

**Problema:** El batch processing bloquea el HTTP request (timeout 120s en frontend).
Con muchas noticias × muchas carteras, puede tardar minutos.

**Solución:** Celery + Redis (o ARQ + Redis para async nativo).

```
Frontend → POST /api/alerts/process-batch/{id}
  → API crea task en cola de Celery
  → Devuelve task_id inmediatamente (HTTP 202 Accepted)
  → Worker Celery procesa en background
  → Frontend poll GET /api/tasks/{task_id} o recibe via SSE
```

### 3.8 ❌ Multi-tenancy completo — PENDIENTE

**Qué:** Aislamiento real de datos por usuario/organización.

- Cada usuario solo ve sus carteras y alertas.
- Quotas por usuario: máximo de carteras, alertas/hora, ingestas/día.
- Roles: `user` (CRUD propio), `admin` (ver todo, gestionar sistema).
- Plan de suscripción: free (1 cartera, 5 activos), pro (ilimitado).

### 3.9 ❌ Auto-fill de activos por ticker — PENDIENTE

**Qué:** Al añadir un activo, el usuario solo introduce ticker + nombre + peso.
El resto (sector, industry, country, ISIN, aliases) se auto-rellena consultando
una API externa.

**Implementación:**

1. **Nuevo endpoint:** `GET /api/assets/lookup?ticker=AAPL`
   - Fuente primaria: Yahoo Finance (`yfinance`) — sector, industry, country, currency.
   - Fuente secundaria: Alpha Vantage OVERVIEW (si hay key) — ISIN, exchange.
   - Devuelve: `{ sector, industry, country, isin, aliases }`.
2. **Frontend:** Botón "Auto-completar" junto al ticker. Llama al endpoint y rellena campos.
3. **El peso NO se auto-rellena** (decisión del inversor).

---

## TIER 4 — Escala y diferenciación

### 4.1 ❌ GPU inference

Para volumen alto de noticias (>1000/día), BART-MNLI en CPU es lento (~500ms-1s/texto).
Opciones: GPU en cloud (AWS/Azure), modelo distilled (`valhalla/distilbart-mnli-12-1`),
o reemplazar NLI por clasificador fine-tuned más ligero.

### 4.2 ❌ API pública para integraciones

Webhooks de alertas + API key para que terceros integren alertas en sus sistemas
(Bloomberg Terminal, trading platforms, Telegram bots).

### 4.3 ❌ Feedback loop para mejora continua

Usar las respuestas "útil/no útil" + backtesting para:
- Ajustar umbrales de severidad/relevancia automáticamente.
- Fine-tune de FinBERT con datos propios etiquetados.
- A/B testing de configuraciones del pipeline.

### 4.4 ❌ Multi-idioma nativo

- Modelos multilingües para NER, sentiment, NLI.
- O pipeline de traducción automática antes del NLP.
- Soporte para noticias en FR, DE, PT además de EN/ES.

### 4.5 ❌ Agrupación de eventos (event clustering)

Cuando Reuters, FT y Bloomberg publican sobre los mismos resultados de Apple:
agrupar en un "cluster de evento" con timeline, en lugar de 3 alertas separadas
(la deduplicación actual previene duplicados, pero no agrupa).

---

## Priorización para un MVP vendible

Si el objetivo es convertir esto en un producto por el que alguien pague $15-30/mes,
este es el orden óptimo de implementación:

| # | Tarea | Tier | Esfuerzo | Estado |
|---|-------|:----:|:--------:|:------:|
| 1 | **Autenticación JWT** | 1 | 1-2 días | ❌ Pendiente |
| 2 | ~~Fix I/O bloqueante~~ | 2 | 0.5 días | ✅ Completado |
| 3 | ~~Fix entity matching~~ | 2 | 0.5 días | ✅ Completado |
| 4 | ~~Docker + docker-compose~~ | 3 | 1 día | ✅ Completado |
| 5 | ~~Deduplicación persistente~~ | 2 | 1 día | ✅ Completado |
| 6 | ~~Cold start preload~~ | 2 | 0.5 días | ✅ Completado |
| 7 | **Rate limiting** (slowapi) | 3 | 0.5 días | ❌ Pendiente |
| 8 | **SSE alertas real-time** | 3 | 1-2 días | ❌ Pendiente |
| 9 | **Logging estructurado + Sentry** | 3 | 1 día | ❌ Pendiente |
| 10 | **Traducción ES→EN** para CNMV | 2 | 0.5 días | Medio |
| 11 | **Backtesting** (yfinance + métricas) | 3 | 2-3 días | Alto |
| 12 | **CI/CD** (GitHub Actions) | 3 | 0.5 días | Medio |
| 13 | **Feedback "útil/no útil"** | 3 | 1 día | Alto |
| 14 | **Task queue** (Celery/ARQ) | 3 | 2 días | Medio |
| 15 | **Landing page + Stripe billing** | 3 | 2-3 días | Crítico (para cobrar) |

**Total estimado para MVP vendible:** ~2-3 semanas de trabajo enfocado.

---

## Qué tiene valor diferencial frente a la competencia

| Funcionalidad | Bloomberg ($24K/año) | Koyfin ($50/mes) | Benzinga Pro ($100/mes) | **InvestAlert** |
|---|---|---|---|---|
| Alertas por cartera personalizada | ✅ | Parcial | ❌ | ✅ |
| NLP (FinBERT + NLI) | Propietario | ❌ | Básico | ✅ |
| Explicación contextual LLM | ❌ | ❌ | ❌ | ✅ |
| Multi-fuente (SEC + CNMV + RSS + APIs) | ✅ | Parcial | Parcial | ✅ |
| Deduplicación semántica | ❌ | ❌ | ❌ | ✅ |
| Precio objetivo | — | — | — | **$15-30/mes** |

**El diferencial clave es la explicación contextualizada a la cartera del usuario vía LLM.**
Nadie en el rango de precio $15-50/mes ofrece esto.
