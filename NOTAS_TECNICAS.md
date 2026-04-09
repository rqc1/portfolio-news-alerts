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
| **Tests unitarios** | Alta | No hay tests. Crear `tests/` con pytest para cada módulo (especialmente relevance, events, impact) |
| **Tests de integración** | Alta | Test end-to-end del pipeline completo: noticia → alerta |
| **Modelo spaCy multilingüe** | Media | Ahora solo se carga `en_core_web_sm`. Falta routing por idioma para cargar `es_core_news_sm` cuando la noticia esté en español (CNMV) |
| **Scheduler de ingesta** | Media | No hay cron ni scheduler. Las ingestas se lanzan manualmente desde la API o el frontend. Implementar con APScheduler o Celery Beat |
| **Logging estructurado** | Media | Ahora se usa `logging` básico. Faltaría configurar rotación de logs, formato JSON y niveles por módulo |
| **Autenticación API** | Baja (prototipo) | No hay autenticación. Para producción, añadir JWT o API keys |
| **Caché de embeddings** | Media | Los embeddings de la cartera se recalculan en cada petición. Cachear en MongoDB o Redis |
| **Corpus etiquetado** | Alta | El documento del TFM prevé un dataset anotado manualmente. Falta crear la estructura de anotación y el script de etiquetado |
| **Evaluación NLP** | Alta | No hay scripts de evaluación (F1, precision, recall, matrices de confusión). Crear `evaluation/` |
| **Event study financiero** | Alta | No hay módulo de evaluación financiera. Implementar una versión simplificada con ventanas temporales y comparación vs. baselines |
| **Pipeline de reentrenamiento** | Baja | No hay flujo para reentrenar modelos con datos nuevos |
| **Docker Compose** | Media | Falta `docker-compose.yml` para levantar MongoDB + API + Streamlit en un solo comando |

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
| **Resolución de entidades** | Alto | Alta | Vincular menciones textuales a entidades canónicas (ej. "Apple", "AAPL", "Apple Inc." → misma entidad). Usar Wikidata o un grafo de conocimiento financiero |
| **Clasificación zero-shot de eventos** | Alto | Baja | En vez del LLM, usar `cross-encoder/nli-deberta-v3-large` con los nombres de la taxonomía como hipótesis (sin coste API) |
| **Multilingüe nativo** | Medio | Media | Cambiar `all-MiniLM-L6-v2` por `paraphrase-multilingual-MiniLM-L12-v2` para soportar noticias en español sin traducir |
| **Summarization** | Medio | Baja | Resumir noticias largas antes de clasificar para mejorar calidad del input a los modelos |
| **Calibración de probabilidades** | Alto | Media | Aplicar Platt scaling o isotonic regression al score de confianza para que sea interpretable como probabilidad real |
| **Ventana temporal de contexto** | Medio | Media | Incorporar noticias previas del mismo activo para contextualizar (ej. "segunda alerta sobre AAPL en 48h") |

### 2.2 Mejoras del Motor de Alertas

| Mejora | Detalle |
|--------|---------|
| **Agrupación de alertas** | Cuando múltiples noticias se refieren al mismo evento, agruparlas en un "cluster de evento" con timeline |
| **Priorización dinámica** | Ajustar umbrales según la hora del día, la volatilidad reciente o el volumen de noticias |
| **Alertas por email/Telegram** | Notificaciones push además de mostrar en dashboard |
| **Feedback del usuario** | Botones "útil/no útil" en cada alerta para reentrenamiento futuro |
| **Score compuesto configurable** | Permitir al usuario ajustar los pesos de relevancia vs. severidad vs. confianza |
| **Modo histórico / backtest** | Ejecutar el pipeline sobre noticias pasadas para evaluar calidad retrospectiva |

### 2.3 Mejoras de Arquitectura

| Mejora | Detalle |
|--------|---------|
| **Cola de mensajes** | Usar RabbitMQ o Redis Streams para desacoplar ingesta y procesamiento |
| **Procesamiento asíncrono** | Mover el pipeline NLP pesado (FinBERT + embeddings) a workers con Celery |
| **Caché de modelos** | Los modelos de Hugging Face se cargan en memoria. Compartir instancia entre workers |
| **Monitorización** | Prometheus + Grafana para métricas de latencia, throughput y errores |
| **Versionado de modelos** | MLflow o Weights & Biases para trackear experimentos y versiones de clasificadores |

### 2.4 Mejoras para la Evaluación Académica

| Mejora | Detalle |
|--------|---------|
| **Ablation study** | Medir el impacto individual de cada módulo (¿cuánto aporta la semántica vs. solo reglas?) |
| **Comparación de baselines** | Baseline 1: solo keywords. Baseline 2: solo FinBERT. Baseline 3: sistema completo |
| **Análisis de falsos positivos** | Documentar alertas erróneas y clasificar el tipo de error |
| **Event study simplificado** | Medir CAR (Cumulative Abnormal Return) en ventanas [-1, +3] días alrededor de las alertas |
| **Inter-annotator agreement** | Si el corpus se etiqueta con más de una persona, medir Cohen's kappa |

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

### 3.3 LLM para Clasificación de Eventos

**Modelo elegido:** `gpt-4o-mini` (API de OpenAI)

**Por qué:**
- Capaz de clasificar en categorías complejas con una sola instrucción
- Entiende contexto financiero sin fine-tuning
- Barato (~$0.15 / 1M tokens input)
- Permite explicar la clasificación (campo `reasoning`)

**Alternativas:**

| Opción | Coste | Calidad | Latencia | Offline |
|--------|-------|---------|----------|---------|
| `gpt-4o-mini` (actual) | ~$0.15/1M tok | Alta | 1-3s | No |
| `gpt-4o` | ~$2.50/1M tok | Muy alta | 2-5s | No |
| **Fallback por keywords** (implementado) | Gratis | Baja-Media | <1ms | Sí |
| Zero-shot NLI (`cross-encoder/nli-deberta-v3-large`) | Gratis | Media-Alta | ~100ms | Sí |
| Fine-tuned BERT sobre corpus propio | Gratis (tras entrenamiento) | Potencialmente alta | ~50ms | Sí |
| Llama 3 / Mistral (local) | Gratis | Alta | 5-30s (CPU) | Sí |

**Estrategia recomendada para el TFM:**
1. Desarrollar con el **fallback por keywords** (funciona sin API key)
2. Evaluar con **zero-shot NLI** como alternativa gratuita y offline
3. Usar **gpt-4o-mini** como gold standard para comparar
4. Si hay corpus anotado suficiente, considerar **fine-tuning de un BERT** como contribución técnica

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
| **NewsAPI.org** | API REST (freemium) | Agregador de +150k fuentes, búsqueda por keyword y fecha | Baja (hay SDK Python) |
| **GNews API** | API REST (gratuita limitada) | Google News programático | Baja |
| **Alpha Vantage News** | API REST (gratuita) | Noticias con tickers anotados y scores de sentimiento | Baja |
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
| 4 | Crear corpus etiquetado (50-100 noticias) para evaluación | Datos | 🔴 Alta |
| 5 | Implementar routing multilingüe spaCy (EN/ES) | NLP | 🟡 Media |
| 6 | Cambiar embeddings a multilingüe | NLP | 🟡 Media |
| 7 | Escribir tests unitarios para módulos core | Testing | 🟡 Media |
| 8 | Implementar scheduler automático de ingesta | Arquitectura | 🟡 Media |
| 9 | Scripts de evaluación NLP (F1, confusion matrix) | Evaluación | 🔴 Alta |
| 10 | Event study simplificado con datos de precios | Evaluación | 🟡 Media |
