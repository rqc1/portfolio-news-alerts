# Notas Técnicas del Proyecto – Pendientes, Mejoras y Decisiones de Diseño

## 1. Elementos Pendientes de Crear o Configurar

### 1.1 Infraestructura

| Elemento | Estado | Descripción |
|----------|--------|-------------|
| MongoDB local | ❌ Pendiente | Instalar MongoDB Community Server o usar Docker: `docker run -d -p 27017:27017 --name mongo mongo:7` |
| Entorno virtual Python | ❌ Pendiente | `python -m venv venv` + instalar `requirements.txt` |
| Modelo spaCy | ❌ Pendiente | `python -m spacy download en_core_web_sm` (inglés). Para español: `python -m spacy download es_core_news_sm` |
| Descarga de FinBERT | ❌ Automática | Se descarga la primera vez que se ejecuta (~1.3 GB). Modelo: `ProsusAI/finbert` |
| Descarga de embeddings | ❌ Automática | `sentence-transformers/all-MiniLM-L6-v2` (~80 MB), se descarga al primer uso |
| API Key OpenAI | ❌ Opcional | Sin ella, el clasificador de eventos funciona con fallback por keywords |
| Variable SEC User-Agent | ⚠️ Configurar | La SEC exige un User-Agent con nombre y email real. Cambiar en `config.py` o `.env` |
| Archivo `.env` | ❌ Pendiente | Copiar `.env.example` a `.env` y rellenar valores reales |

### 1.2 Código por Desarrollar

| Componente | Prioridad | Descripción |
|------------|-----------|-------------|
| **Tests unitarios** | ✅ Hecho | +200 tests con pytest cubriendo portfolio, nlp, relevance, events, impact, alerts, llm, ingestion, notifications, scheduler, market, analytics, evaluation, backtest y security |
| **Tests de integración** | Alta | Test end-to-end del pipeline completo: noticia → alerta |
| **Modelo spaCy multilingüe** | Media | Ahora solo se carga `en_core_web_sm`. Se traduce ES→EN con `deep-translator` antes del pipeline NLP. Falta routing por idioma para cargar `es_core_news_sm` como mejora futura |
| **Scheduler de ingesta** | ✅ Hecho | Implementado con APScheduler en `modules/scheduler/`. Ingesta RSS+CNMV cada 15min, alertas cada 20min, limpieza diaria. Configurable via env vars |
| **Logging estructurado** | ✅ Hecho | `structlog` con formato JSON, niveles configurables y `request-id` propagado por contexto en `modules/security/logging_config.py`. Activable via `LOG_JSON`/`LOG_LEVEL` |
| **Autenticación API** | ✅ Hecho | JWT (HS256, `python-jose`) + hash de contraseñas con `bcrypt` en `modules/security/auth.py`. Endpoints `/api/auth/register|login|me`. Protege backtest/calibración. Modo anónimo configurable (`AUTH_ENABLED`, default false) para no romper frontend/tests |
| **Caché de embeddings** | Media | Los embeddings de la cartera se recalculan en cada petición. Cachear en MongoDB o Redis. Nota: la deduplicación ahora sí persiste embeddings en MongoDB (`dedup_embeddings` con TTL) |
| **Caché de resultados LLM** | Media | Las respuestas LLM no se cachean. Para noticias similares, cachear por content_hash ahorraría tokens |
| **Corpus etiquetado** | ✅ Hecho | `evaluation/dataset.jsonl` (40 noticias bilingües) + `portfolios.json` (3 carteras de referencia), esquema validado con Pydantic (`evaluation/schema.py`) |
| **Evaluación NLP** | ✅ Hecho | Paquete `evaluation/`: métricas en Python puro (`metrics.py`), estudio de ablación de 4 variantes (`run_ablation.py`, resultados en `results/`) y acuerdo inter-anotador (`agreement.py`, κ de Cohen / κ ponderado / α de Krippendorff) |
| **Event study financiero** | ✅ Hecho | `modules/backtest/event_study.py` calcula AR/CAR (metodología MacKinlay, 1997) en ventanas alrededor de cada alerta; `modules/backtest/service.py` añade backtesting y autocalibración de umbrales. Endpoints `/api/backtest/{id}` y `/api/backtest/{id}/calibrate` |
| **Pipeline de reentrenamiento** | Baja | No hay flujo para reentrenar modelos con datos nuevos |
| **Docker Compose** | ✅ Hecho | `Dockerfile` multi-stage + `docker-compose.yml` (MongoDB + API + Frontend) + `frontend/Dockerfile`. Levantar con `docker-compose up --build` |
| **Datos de mercado (yfinance)** | ✅ Hecho | `modules/market/` — lookup de activos, precios actuales, histórico OHLCV. 4 endpoints API. Auto-fill en frontend |
| **Métricas de cartera (quantstats)** | ✅ Hecho | `modules/analytics/` — Sharpe, Sortino, VaR, drawdown, alpha/beta, rendimiento por activo. Dashboard con KPIs + gráficos |
| **Asesor de inversiones** | ✅ Hecho | `modules/advisor/` — Cuestionario MiFID, perfilado de riesgo, informes con LLM (CFA/CAIA/CFP) + fallback determinista |

### 1.3 Datos Pendientes

| Dataset | Descripción |
|---------|-------------|
| **Mapeo ticker → CIK** | Para buscar filings por empresa en SEC EDGAR. La SEC ofrece `company_tickers.json` pero hay que integrarlo como lookup |
| **Mapeo ticker → ISIN español** | Para cruzar con noticias CNMV. Fuente posible: BME o CNMV |
| **Corpus de evaluación** | Subconjunto de noticias etiquetado manualmente con: relevancia, tipo de evento, dirección, severidad |
| **Universo de activos** | Definir las 15-30 empresas del prototipo (mezcla S&P 500 + IBEX 35) |

---

## 2. Posibles Mejoras

### 2.1 Mejoras del Pipeline NLP

| Mejora | Impacto | Complejidad | Detalle |
|--------|---------|-------------|---------|
| **Modelo NER financiero especializado** | Alto | Media | Cambiar spaCy genérico por un NER entrenado en textos financieros (ej. `flair/ner-english-ontonotes-large` o entrenar propio con SENTiVENT) |
| **Resolución de entidades** | Alto | Alta | ✅ **IMPLEMENTADO**: `modules/nlp/entity_resolver.py` vincula menciones textuales a entidades canónicas ("Apple", "AAPL", "Apple Inc." → misma entidad) mediante alias normalizados y mapeo a ticker |
| **Clasificación zero-shot de eventos** | Alto | Baja | ✅ **IMPLEMENTADO**: `facebook/bart-large-mnli` reemplaza al LLM para esta tarea. Sin coste API, offline, ~200ms |
| **Multilingüe nativo** | Medio | Media | Cambiar `all-MiniLM-L6-v2` por `paraphrase-multilingual-MiniLM-L12-v2` para soportar noticias en español sin traducir. Actualmente se traduce ES→EN con `deep-translator` |
| **Summarization** | Medio | Baja | Resumir noticias largas antes de clasificar para mejorar calidad del input a los modelos |
| **Calibración de probabilidades** | Alto | Media | ✅ **IMPLEMENTADO (severidad)**: `modules/impact/calibration.py` aprende una correspondencia severidad-estimada → severidad-real a partir de las etiquetas, corrigiendo sesgos. Pendiente extender a Platt/isotonic sobre el score de confianza |
| **Ventana temporal de contexto** | Medio | Media | Incorporar noticias previas del mismo activo para contextualizar (ej. "segunda alerta sobre AAPL en 48h") |

### 2.2 Mejoras del Motor de Alertas

| Mejora | Detalle |
|--------|---------|
| **Agrupación de alertas** | Cuando múltiples noticias se refieren al mismo evento, agruparlas en un "cluster de evento" con timeline |
| **Priorización dinámica** | Ajustar umbrales según la hora del día, la volatilidad reciente o el volumen de noticias |
| **Alertas por email/Telegram** | ✅ Implementado en `modules/notifications/`. Email SMTP (HTML profesional + plaintext) + Webhook HTTP POST (Slack/Discord/Telegram). Se disparan automáticamente al generar una alerta |
| **Feedback del usuario** | Parcial | Bucle de retroalimentación implementado: el endpoint `/api/backtest/{id}/calibrate` reajusta umbrales de relevancia/severidad con la evidencia acumulada (AR/CAR). Pendiente la UI de botones "útil/no útil" |
| **Score compuesto configurable** | Permitir al usuario ajustar los pesos de relevancia vs. severidad vs. confianza |
| **Modo histórico / backtest** | ✅ Implementado en `modules/backtest/`. Ejecuta el pipeline sobre el historial de alertas y mide la capacidad direccional agregada (`/api/backtest/{id}`) |
| **Comparativa LLM vs. determinista** | Registrar ambos análisis (LLM y determinista) para cada alerta y comparar calidad en evaluación |

### 2.3 Mejoras de Arquitectura

| Mejora | Detalle |
|--------|---------|
| **Cola de mensajes** | Usar RabbitMQ o Redis Streams para desacoplar ingesta y procesamiento |
| **Procesamiento asíncrono** | Mover el pipeline NLP pesado (FinBERT + embeddings) a workers con Celery |
| **Caché de modelos** | Los modelos de Hugging Face se cargan en memoria. Compartir instancia entre workers |
| **Monitorización** | ✅ Métricas Prometheus implementadas en `modules/security/metrics.py` (latencia/volumen HTTP, consumo de tokens y coste LLM), expuestas en `/metrics`. Pendiente el panel Grafana |
| **Versionado de modelos** | MLflow o Weights & Biases para trackear experimentos y versiones de clasificadores |

### 2.4 Mejoras para la Evaluación Académica

| Mejora | Detalle |
|--------|---------|
| **Ablation study** | ✅ Implementado: `evaluation/run_ablation.py` mide 4 variantes (reglas / híbrida / híbrida+NLI / completa). Resultados en `evaluation/results/ablation_summary.json` |
| **Comparación de baselines** | Baseline 1: solo keywords. Baseline 2: solo FinBERT. Baseline 3: sistema completo sin LLM. Baseline 4: sistema completo con LLM |
| **Análisis de falsos positivos** | Documentar alertas erróneas y clasificar el tipo de error |
| **Event study simplificado** | ✅ Implementado: `modules/backtest/event_study.py` mide CAR en ventanas alrededor de las alertas |
| **Inter-annotator agreement** | ✅ Implementado: `evaluation/agreement.py` calcula κ de Cohen, κ ponderado (severidad) y α de Krippendorff. Resultados: relevancia κ=0,86; evento κ=1,0; dirección κ=0,88; severidad κ-pond=0,82; α global=0,91 |
| **LLM vs. determinista A/B test** | Comparar calidad de alertas con y sin LLM contextual en el mismo corpus |

---

## 3. Selección de Modelos: Criterios y Alternativas

### 3.1 FinBERT – Sentiment Analysis

**Modelo elegido:** `ProsusAI/finbert`

**Por qué este modelo:**
- Preentrenado sobre textos financieros (Reuters TRC2, comunicados financieros)
- Fine-tuned específicamente para sentiment en dominio financiero
- Referenciado en el estado de la cuestión del TFM (Araci, 2019)
- Gratuito y de código abierto
- Salida de 3 clases (positive, negative, neutral) alineada con la necesidad del sistema

**Alternativas consideradas:**

| Modelo | Ventaja | Inconveniente | Cuándo usarlo |
|--------|---------|---------------|---------------|
| `yiyanghkust/finbert-tone` | Entrenado sobre analyst reports | Menos generalista | Si el foco son informes de analistas |
| `cardiffnlp/twitter-roberta-base-sentiment-latest` | Bueno para texto corto/informal | No es dominio financiero | Si se añaden redes sociales |
| `mrm8488/distilroberta-finetuned-financial-news-sentiment-analysis` | Más ligero (distilled) | Menor precisión | Si hay restricciones de memoria/GPU |
| Zero-shot con NLI | Sin entrenamiento específico | Menos preciso en sentimiento | Para prototipado rápido |
| **GPT-4o-mini** | Muy flexible, entiende contexto | Coste por token, latencia | Para noticias ambiguas donde FinBERT no basta |

**Criterios de selección:**
1. **Dominio**: el modelo debe estar entrenado o fine-tuned en texto financiero
2. **Tamaño**: preferir modelos que quepan en CPU para el prototipo (~400 MB)
3. **Validación académica**: preferir modelos citados en papers del campo
4. **Licencia**: open-source para reproducibilidad
5. **Latencia**: inferencia en menos de 200ms por texto en CPU

### 3.2 Sentence Transformers – Embeddings Semánticos

**Modelo elegido:** `sentence-transformers/all-MiniLM-L6-v2`

**Por qué:**
- Buen balance entre calidad y velocidad (80 MB, 384 dimensiones)
- Soporta textos hasta 256 tokens (suficiente para titulares y resúmenes)
- Top-5 en MTEB benchmark para su tamaño

**Alternativas:**

| Modelo | Dimensiones | Velocidad | Cuándo |
|--------|-------------|-----------|--------|
| `all-MiniLM-L12-v2` | 384 | Algo más lento | Si se necesita mejor calidad sin multilingüe |
| `paraphrase-multilingual-MiniLM-L12-v2` | 384 | Similar | **Recomendado** si se procesan noticias en español y en inglés |
| `BAAI/bge-small-en-v1.5` | 384 | Rápido | Alternativa más moderna, buen rendimiento |
| `intfloat/e5-small-v2` | 384 | Rápido | Requiere prefijos "query:" y "passage:" |
| `nomic-ai/nomic-embed-text-v1.5` | 768 | Medio | Mayor expresividad, más pesado |

**Recomendación para el TFM:** Si finalmente se procesan noticias en español (CNMV), cambiar a `paraphrase-multilingual-MiniLM-L12-v2`. Solo requiere cambiar una línea en `config.py`.

### 3.3 LLM para Análisis Contextual de Impacto y Explicaciones

**Arquitectura:** Cliente multi-proveedor con API compatible OpenAI.

**Proveedores soportados:**

| Proveedor | Base URL | Coste | Modelos destacados | Cuándo usarlo |
|-----------|----------|-------|--------------------|--------------|
| **GitHub Models** (por defecto) | `models.inference.ai.azure.com` | Gratuito con GitHub Token | Llama 3.1 8B, Mistral, Phi-3 | Desarrollo y prototipado |
| **HuggingFace Inference** | `api-inference.huggingface.co/v1` | Tier gratuito (rate limited) | Llama 3.1 8B, Mistral 7B | Alternativa gratuita |
| **OpenAI** | `api.openai.com/v1` | ~$0.15/1M tokens (gpt-4o-mini) | gpt-4o-mini, gpt-4o | Producción, máxima calidad |
| **Ollama** (local) | `localhost:11434/v1` | Gratuito, sin internet | llama3.1, mistral, phi3 | Offline, sin coste, privacidad |

**Uso actual en el pipeline:**
- **Análisis contextual de impacto**: dirección + severidad + confianza contextualizados a la cartera
- **Generación de explicaciones personalizadas**: texto en español que explica *por qué* la noticia importa para *esta* cartera
- **Filtro de relevancia de segundo nivel**: para noticias borderline, detecta relevancia indirecta (competidores, proveedores, regulación sectorial)

**Estrategia de fallback:** Si el LLM no está disponible, el sistema funciona al 100% con:
- Estimación de impacto determinista (priors fijos + heurísticas)
- Explicaciones con template
- Sin filtro de relevancia de segundo nivel

**Decisión de diseño clave:** El LLM ya NO se usa para clasificar el tipo de evento (esa tarea
la resuelve el modelo zero-shot NLI local, sin coste). El LLM se reserva para las tareas
donde aporta mayor valor diferencial: razonamiento contextual sobre el impacto específico
en la cartera del usuario.

### 3.4 spaCy – NER

**Modelo elegido:** `en_core_web_sm` (inglés, 12 MB)

**Alternativas:**

| Modelo | Tamaño | Precisión NER | Cuándo |
|--------|--------|---------------|--------|
| `en_core_web_sm` (actual) | 12 MB | Aceptable | Prototipo rápido |
| `en_core_web_trf` | ~400 MB | Mejor | Si se necesita NER más preciso y hay GPU |
| `es_core_news_sm` | 12 MB | Aceptable | Para noticias CNMV en español |
| `xx_ent_wiki_sm` | 11 MB | Moderada | Multilingüe pero menos preciso |

**Pendiente:** Implementar routing automático según el idioma detectado por `langdetect`.

---

## 4. Fuentes de Noticias: Detalle Técnico

### 4.1 SEC EDGAR (Estados Unidos)

| Campo | Valor |
|-------|-------|
| **URL base** | `https://efts.sec.gov/LATEST/search-index` (full-text search) |
| **URL por empresa** | `https://data.sec.gov/submissions/CIK{cik_padded}.json` |
| **Autenticación** | No requiere. Exige `User-Agent` con nombre y email |
| **Rate limit** | 10 peticiones/segundo |
| **Tipos de filing relevantes** | `8-K` (eventos materiales), `10-K` (informe anual), `10-Q` (trimestral) |
| **Formato** | JSON (metadatos), HTML/XBRL (contenido del filing) |
| **Cobertura** | Todas las empresas cotizadas en EE.UU. |
| **Latencia** | Filings disponibles minutos después de ser registrados |
| **Coste** | Gratuito |

**8-K es la fuente más valiosa**: reporta eventos materiales (resultados inesperados, cambios directivos, M&A, litigios, etc.) exactamente en la taxonomía del TFM.

**Limitación actual:** El módulo `sec_edgar.py` usa el buscador full-text, que no siempre devuelve resultados estructurados. Para mejorar: usar la API de submissions por CIK para cada empresa en cartera.

### 4.2 CNMV (España)

| Campo | Valor |
|-------|-------|
| **Hechos relevantes** | `https://www.cnmv.es/Portal/Publicaciones/RSSHechosRelev.aspx` |
| **Información privilegiada** | `https://www.cnmv.es/Portal/Publicaciones/RSSInfoPrivilegiada.aspx` |
| **Notas de prensa** | `https://www.cnmv.es/Portal/Publicaciones/RSSNotasPrensa.aspx` |
| **Formato** | RSS/XML |
| **Idioma** | Español |
| **Cobertura** | Empresas cotizadas en BME (Bolsas y Mercados Españoles) |
| **Coste** | Gratuito |

**Hechos relevantes** es el equivalente español al 8-K: incluye comunicados obligatorios de empresas cotizadas sobre eventos que pueden afectar al precio.

**Limitación actual:** Los feeds RSS de la CNMV solo incluyen título y resumen corto. Para el texto completo, habría que seguir el enlace y hacer scraping del HTML de la CNMV.

### 4.3 Feeds RSS Genéricos

| Feed | URL | Tipo de contenido | Idioma |
|------|-----|-------------------|--------|
| Reuters Business | `https://feeds.reuters.com/reuters/businessNews` | Noticias corporativas globales | EN |
| Yahoo Finance | `https://finance.yahoo.com/news/rssindex` | Noticias financieras generales | EN |
| Financial Times | `https://www.ft.com/rss/home` | Análisis y noticias premium | EN |
| Seeking Alpha | `https://seekingalpha.com/market_currents.xml` | Análisis de inversión | EN |
| Investing.com | `https://www.investing.com/rss/news.rss` | Noticias de mercado | EN |

**Limitaciones de los RSS:**
- **Texto parcial:** La mayoría de feeds solo incluyen título + resumen (no el artículo completo)
- **Rate limiting:** Algunos medios bloquean peticiones frecuentes
- **Cambios de URL:** Los feeds pueden cambiar o desaparecer sin aviso
- **Sesgos:** Cada medio tiene su línea editorial y cobertura geográfica

### 4.4 Fuentes Adicionales Recomendadas (no implementadas aún)

| Fuente | Tipo | Interés | Dificultad |
|--------|------|---------|------------|
| **NewsAPI.org** | API REST (freemium) | Agregador de +150k fuentes, búsqueda por keyword y fecha | Baja (hay SDK Python) | ✅ Implementado |
| **GNews API** | API REST (gratuita limitada) | Google News programático | Baja |
| **Alpha Vantage News** | API REST (gratuita) | Noticias con tickers anotados y scores de sentimiento | Baja | ✅ Implementado |
| **Benzinga** | API (de pago) | Noticias financieras de alta calidad con metadata rica | Media |
| **Twitter/X Financial** | API (de pago) | Señales tempranas pero muy ruidosas | Alta |
| **Earnings call transcripts** | Web scraping / APIs | Transcripciones de presentaciones de resultados | Media-Alta |
| **BME Market Data** | API/RSS | Datos del mercado español | Media |
| **ECB/Fed comunicados** | RSS/Web | Política monetaria y estabilidad financiera | Baja |

### 4.5 Estrategia Recomendada de Fuentes para el TFM

Para un prototipo académico viable, se recomienda priorizar así:

1. **Imprescindibles** (ya implementadas):
   - SEC EDGAR 8-K → eventos materiales de empresas US
   - CNMV hechos relevantes → eventos de empresas españolas
   - 2-3 feeds RSS generalistas (Reuters, Yahoo Finance)

2. **Recomendables** (mejoran cobertura):
   - Alpha Vantage News Sentiment API (gratuita, 25 peticiones/día)
   - NewsAPI.org plan gratuito (100 peticiones/día)

3. **Opcionales** (para enriquecer el análisis):
   - Comunicados de bancos centrales (BCE, Fed)
   - Scraping de la web de Relaciones con Inversores de las empresas del universo

---

## 5. Resumen de Próximos Pasos Prioritarios

| # | Tarea | Tipo | Prioridad |
|---|-------|------|-----------|
| 1 | Instalar MongoDB y dependencias Python | Infraestructura | 🔴 Alta |
| 2 | Definir universo de 15-20 activos (S&P 500 + IBEX 35) | Datos | 🔴 Alta |
| 3 | Primera ingesta real y verificar pipeline E2E | Validación | 🔴 Alta |
| 4 | ~~Crear corpus etiquetado (40 noticias) para evaluación~~ | Datos | ✅ Hecho |
| 5 | Implementar routing multilingüe spaCy (EN/ES) | NLP | 🟡 Media |
| 6 | Cambiar embeddings a multilingüe | NLP | 🟡 Media |
| 7 | ~~Escribir tests unitarios para módulos core~~ | Testing | ✅ Hecho |
| 8 | ~~Implementar scheduler automático de ingesta~~ | Arquitectura | ✅ Hecho |
| 9 | ~~Scripts de evaluación NLP (F1, confusion matrix)~~ | Evaluación | ✅ Hecho |
| 10 | ~~Event study simplificado con datos de precios~~ | Evaluación | ✅ Hecho |
| 11 | ~~Acuerdo inter-anotador (Cohen's kappa)~~ | Evaluación | ✅ Hecho |
| 12 | ~~Capa de producción (JWT, logs, métricas, rate limit)~~ | Arquitectura | ✅ Hecho |

> **Para la hoja de ruta completa de producción** (autenticación, Docker, CI/CD, escalabilidad,
> monetización), ver [`ROADMAP.md`](ROADMAP.md).

---

## 6. Capa de Producción: Seguridad y Observabilidad

El paquete `modules/security/` añade la capa operativa necesaria para un despliegue
seguro y observable. Todos sus componentes siguen el principio de **degradación elegante**:
están desactivados o en modo permisivo por defecto y se habilitan via variables de entorno,
de modo que el sistema sigue siendo ejecutable en local sin infraestructura adicional.

| Componente | Archivo | Detalle |
|------------|---------|---------|
| **Autenticación JWT** | `auth.py` | Tokens HS256 (`python-jose`) + hash `bcrypt`. Endpoints `/api/auth/register|login|me`. Modo anónimo si `AUTH_ENABLED=false` |
| **Logging estructurado** | `logging_config.py` | `structlog` con `request-id` por contexto; salida JSON (`LOG_JSON`) o consola |
| **Métricas Prometheus** | `metrics.py` | Latencia/volumen HTTP, peticiones/tokens/coste LLM; expuestas en `/metrics` |
| **Rate limiting** | `main.py` (slowapi) | Límite por IP (`RATE_LIMIT_DEFAULT`), configurable |
| **CORS restringido** | `main.py` | `CORS_ORIGINS` explícitos en lugar de comodín |
| **Health probes** | `main.py` | `/health/live`, `/health/ready` (503 si DB caída), `/health/db` |

### Decisión de diseño: bcrypt directo en lugar de passlib

`passlib 1.7.4` es **incompatible con `bcrypt 5.0.0`** (lee el atributo eliminado
`bcrypt.__about__` y lanza `ValueError` con contraseñas de más de 72 bytes). Por ello
`auth.py` usa la librería `bcrypt` **directamente**, truncando explícitamente la contraseña
a 72 bytes UTF-8 antes de `hashpw`/`checkpw`. Así se evita la dependencia rota sin sacrificar
seguridad.

### Variables de configuración añadidas (`config.py`)

`CORS_ORIGINS`, `AUTH_ENABLED` (default `false`), `JWT_SECRET`, `JWT_ALGORITHM` (HS256),
`JWT_EXPIRE_MINUTES` (1440), `RATE_LIMIT_DEFAULT` (`120/minute`), `RATE_LIMIT_AUTH`
(`10/minute`), `RATE_LIMIT_ENABLED`, `LOG_JSON`, `LOG_LEVEL`, `METRICS_ENABLED`,
`LLM_COST_PER_1K_PROMPT`, `LLM_COST_PER_1K_COMPLETION`, `SEVERITY_CALIBRATOR_PATH`.

> ⚠️ **Seguridad**: el archivo `.env` contiene credenciales reales (SMTP, claves API).
> Asegúrate de que está en `.gitignore` y rota cualquier secreto que se haya compartido.
