# Herramientas Open Source para Inversiones

> Análisis de software libre relevante para el ecosistema de InvestAIlert y el ámbito de inversiones en general.  
> Fecha de investigación: Abril 2026

---

## Índice

1. [Herramientas útiles para InvestAIlert](#1-herramientas-útiles-para-investailert)
2. [Herramientas de interés general (fuera de scope actual)](#2-herramientas-de-interés-general-fuera-de-scope-actual)
3. [Resumen comparativo](#3-resumen-comparativo)

---

## 1. Herramientas útiles para InvestAIlert

Estas herramientas pueden integrarse directamente en el proyecto o complementar funcionalidades existentes del sistema de alertas.

---

### 1.1 yfinance

| | |
|---|---|
| **Repositorio** | https://github.com/ranaroussi/yfinance |
| **Stars** | ~23.000 |
| **Licencia** | Apache 2.0 |
| **Lenguaje** | Python |
| **Estado** | Mantenimiento activo (última release: abril 2026) |

**Descripción**: Librería Python que permite descargar datos financieros y de mercado desde la API pública de Yahoo Finance de forma sencilla y pythonica. Es la librería más popular del ecosistema Python para obtener datos de mercado.

**Funcionalidades principales**:
- Datos históricos de precios (OHLCV) con granularidad desde 1 minuto hasta mensual.
- Información fundamental de empresas: sector, industria, país, capitalización, ratios financieros, dividendos, splits.
- Streaming en tiempo real mediante WebSocket (`WebSocket` y `AsyncWebSocket`).
- Búsqueda de tickers y noticias (`Search`).
- Información sectorial e industrial (`Sector`, `Industry`).
- Screener de mercado con queries personalizadas (`EquityQuery`, `Screener`).

**Aplicación en InvestAIlert** (✅ **INTEGRADO** en `modules/market/service.py`):
- **Auto-fill de activos**: Al crear un activo en la cartera, introducir solo el ticker y auto-rellenar nombre, sector, industria, país y tipo de activo mediante `MarketService.lookup_ticker()`. Botón "Auto-fill" en el frontend.
- **Precios en tiempo real**: `MarketService.get_price()` y `get_prices_batch()` para precios actuales + variación diaria. El advisor usa precios reales para enriquecer recomendaciones.
- **Histórico OHLCV**: `MarketService.get_history()` para descargar datos de precios por periodo.
- **Datos para analytics**: `yf.download()` alimenta el módulo `analytics/` con retornos históricos para calcular métricas de cartera.

**Ejemplo de uso**:
```python
import yfinance as yf

ticker = yf.Ticker("AAPL")
info = ticker.info
# info["sector"] → "Technology"
# info["industry"] → "Consumer Electronics"  
# info["country"] → "United States"
# info["marketCap"] → 3200000000000
```

**Consideraciones**: Yahoo Finance es para uso personal/educativo. No es una fuente de datos de nivel institucional. Los datos pueden tener retrasos de 15-20 minutos en algunos mercados.

---

### 1.2 FinGPT

| | |
|---|---|
| **Repositorio** | https://github.com/AI4Finance-Foundation/FinGPT |
| **Stars** | ~19.500 |
| **Licencia** | MIT |
| **Lenguaje** | Python (PyTorch) |
| **Estado** | Activo (AI4Finance Foundation) |

**Descripción**: Proyecto open-source de LLMs (Large Language Models) específicos para finanzas, desarrollado por la AI4Finance Foundation. Proporciona modelos de lenguaje fine-tuneados con datos financieros que superan en rendimiento a modelos genéricos como GPT-4 en tareas financieras específicas.

**Funcionalidades principales**:
- **Análisis de sentimiento financiero** (state-of-the-art): FinGPT v3 supera a GPT-4, ChatGPT y FinBERT en benchmarks estándar (FPB, FiQA-SA, TFNS, NWGI).
- **NER financiero**: Extracción de entidades financieras (empresas, personas, localizaciones) con modelos especializados.
- **Clasificación de titulares**: Análisis de titulares financieros y su dirección de precio.
- **Forecaster (Robo-Advisor)**: Predicción de movimiento de precios basada en noticias y fundamentales.
- **RAG financiero**: Retrieval-Augmented Generation para sentiment analysis con conocimiento externo.
- Fine-tuning con LoRA de bajo coste (~$17 en una RTX 3090).

**Benchmarks de sentiment analysis** (accuracy):

| Modelo | FPB | FiQA-SA | TFNS | Coste |
|---|---|---|---|---|
| **FinGPT v3.3** | **0.882** | **0.874** | **0.903** | ~$17 |
| OpenAI Fine-tune | 0.878 | 0.887 | 0.883 | Variable |
| GPT-4 | 0.833 | 0.630 | 0.808 | API |
| **FinBERT** (actual) | **0.880** | **0.596** | **0.733** | Gratis (local) |

**Aplicación en InvestAIlert**:
- **Reemplazar o complementar FinBERT**: Los modelos FinGPT de sentiment analysis (disponibles en HuggingFace) ofrecen mejor rendimiento que FinBERT, especialmente en FiQA-SA (+46%) y TFNS (+23%).
- **RAG financiero**: Aplicar FinGPT-RAG para mejorar el análisis de sentimiento incorporando contexto externo.
- **NER financiero mejorado**: Reemplazar `spaCy en_core_web_sm` con modelos FinGPT especializados en entidades financieras.

**Consideraciones**: Los modelos completos (Llama2-13B) requieren GPU con 24GB VRAM. Los modelos cuantizados (8-bit, QLoRA) funcionan en RTX 3090 con rendimiento ligeramente inferior. Para un TFM, la versión cuantizada es la opción más práctica.

**Modelos disponibles en HuggingFace**:
- `FinGPT/fingpt-sentiment_llama2-13b_lora` — Sentiment analysis (mejor rendimiento)
- `FinGPT/fingpt-forecaster_dow30_llama2-7b_lora` — Predicción de movimiento de precios
- Modelos multi-tarea basados en Llama2, Falcon, ChatGLM, Qwen

---

### 1.3 OpenBB

| | |
|---|---|
| **Repositorio** | https://github.com/OpenBB-finance/OpenBB |
| **Stars** | ~40.000+ |
| **Licencia** | AGPL-3.0 |
| **Lenguaje** | Python |
| **Estado** | Muy activo, respaldado por empresa (OpenBB Inc.) |

**Descripción**: Plataforma de datos financieros open-source diseñada para analistas, quants y agentes de IA. Proporciona una API unificada para acceder a múltiples fuentes de datos financieros (fundamentales, precios, noticias, macro, opciones, crypto, etc.) desde una única interfaz.

**Funcionalidades principales**:
- API unificada que agrega datos de decenas de proveedores (Yahoo Finance, Alpha Vantage, FRED, SEC Edgar, etc.).
- Terminal interactiva para exploración de datos.
- SDK Python para integración programática.
- Soporte para agentes de IA (OpenBB Agents).
- Datos macroeconómicos, fundamentales, técnicos, noticias y regulatorios.

**Aplicación en InvestAIlert**:
- **Fuente de datos unificada**: En lugar de mantener integraciones separadas con Alpha Vantage, SEC Edgar, NewsAPI y RSS feeds, OpenBB podría servir como capa de abstracción única.
- **Datos macroeconómicos**: Indicadores como tipos de interés, inflación, PIB que afectan a carteras pero que actualmente no capturamos.
- **Enriquecimiento de alertas**: Añadir contexto de mercado (índices, volatilidad, correlaciones) a las alertas generadas.

**Consideraciones**: La licencia AGPL-3.0 requiere que cualquier software que use OpenBB como servicio web también sea open-source. Para un TFM académico esto no es problema, pero es relevante para uso comercial futuro. La plataforma es muy completa pero puede ser excesiva para nuestras necesidades actuales.

---

### 1.4 FinanceDatabase

| | |
|---|---|
| **Repositorio** | https://github.com/JerBouma/FinanceDatabase |
| **Stars** | ~4.000+ |
| **Licencia** | MIT |
| **Lenguaje** | Python |
| **Estado** | Activo |

**Descripción**: Base de datos offline con más de 300.000 símbolos financieros incluyendo equities, ETFs, fondos de inversión, índices, divisas y criptomonedas. Cada entrada incluye metadatos como nombre, sector, industria, país, exchange e ISIN.

**Funcionalidades principales**:
- Búsqueda de activos por nombre, ticker, sector, industria, país o exchange.
- Cobertura global: mercados de EE.UU., Europa, Asia, Latinoamérica.
- Datos offline (no requiere API key ni conexión a internet para búsquedas).
- Clasificación sectorial e industrial estandarizada.
- Integración con FinanceToolkit para análisis posterior.

**Aplicación en InvestAIlert**:
- **Auto-fill de activos (alternativa offline a yfinance)**: Lookup instantáneo de sector, industria y país por ticker sin necesidad de llamadas a API externas.
- **Validación de tickers**: Verificar que un ticker introducido por el usuario existe y es válido.
- **Mejora del matching de relevancia**: Usar la clasificación sectorial estandarizada para mejorar el matching entre noticias y activos de la cartera.
- **Soporte multi-mercado**: Ampliar la cobertura de activos más allá de EE.UU. (mercados europeos, IBEX35, etc.).

**Ejemplo de uso**:
```python
from financedatabase import Equities

equities = Equities()
apple = equities.search(name="Apple")
# Devuelve: sector, industry, country, exchange, currency, ISIN...

tech_spain = equities.search(country="Spain", sector="Technology")
```

**Consideraciones**: Los datos son estáticos (actualizados periódicamente por el mantenedor). No proporciona precios ni datos en tiempo real. Es complementario a yfinance: FinanceDatabase para metadatos y yfinance para datos de mercado.

---

### 1.5 FinanceToolkit

| | |
|---|---|
| **Repositorio** | https://github.com/JerBouma/FinanceToolkit |
| **Stars** | ~3.000+ |
| **Licencia** | MIT |
| **Lenguaje** | Python |
| **Estado** | Activo (mismo autor que FinanceDatabase) |

**Descripción**: Framework de análisis financiero transparente y extensible. Calcula más de 150 ratios y métricas financieras (rentabilidad, solvencia, valoración, riesgo, técnicos) para cualquier activo cotizado.

**Funcionalidades principales**:
- Ratios de rentabilidad (ROE, ROA, margen neto, margen operativo).
- Ratios de valoración (P/E, P/B, EV/EBITDA, PEG).
- Ratios de solvencia y liquidez (current ratio, debt/equity, interest coverage).
- Modelos de valoración (DCF, Gordon Growth).
- Indicadores técnicos (RSI, MACD, Bollinger Bands, SMA/EMA).
- Análisis de riesgo (VaR, CVaR, Sharpe, Sortino, máximo drawdown).

**Aplicación en InvestAIlert**:
- **Panel de análisis de cartera**: Añadir métricas de riesgo y rendimiento al dashboard (Sharpe ratio, drawdown, VaR).
- **Contextualización de alertas**: Enriquecer alertas con datos fundamentales del activo afectado (P/E, deuda, márgenes) para evaluar mejor el impacto.
- **Detección de vulnerabilidades**: Identificar activos en la cartera con alta deuda o valoraciones extremas que podrían ser más susceptibles a eventos negativos.

**Consideraciones**: Requiere API key de FinancialModelingPrep para algunos datos (plan gratuito disponible con límites). Es una herramienta de análisis, no de datos en tiempo real.

---

### 1.6 quantstats

| | |
|---|---|
| **Repositorio** | https://github.com/ranaroussi/quantstats |
| **Stars** | ~5.000+ |
| **Licencia** | Apache 2.0 |
| **Lenguaje** | Python |
| **Estado** | Activo (mismo autor que yfinance) |

**Descripción**: Librería de analytics para portfolios orientada a quants. Genera informes completos de rendimiento, riesgo y métricas de portfolio con una sola línea de código. Incluye generación de informes HTML.

**Funcionalidades principales**:
- Métricas de rendimiento: retornos acumulados, anualizados, por periodo.
- Métricas de riesgo: Sharpe, Sortino, Calmar, máximo drawdown, VaR.
- Comparación con benchmarks (S&P 500, MSCI World, etc.).
- Generación automática de informes HTML con gráficos.
- Análisis de drawdowns, rolling statistics, distribución de retornos.
- Integración directa con pandas.

**Aplicación en InvestAIlert** (✅ **INTEGRADO** en `modules/analytics/service.py`):
- **Métricas de cartera**: `AnalyticsService.compute_metrics()` calcula Sharpe, Sortino, Calmar, VaR, CVaR, max drawdown, volatilidad, alpha, beta y win rate.
- **Dashboard mejorado**: KPI cards y gráficos (retorno acumulado + rendimiento por activo) alimentados por quantstats en la página de dashboard.
- **Comparación con benchmark**: Alpha y beta vs SPY (o benchmark configurable).
- **Rendimiento por activo**: Desglose individual con retorno, volatilidad, Sharpe y contribución al portfolio.

**Ejemplo de uso**:
```python
import quantstats as qs

# Extender pandas con métodos de quantstats
qs.extend_pandas()

# Generar informe HTML completo
qs.reports.html(returns, benchmark="SPY", output="portfolio_report.html")
```

**Consideraciones**: Orientada a análisis retrospectivo (backtesting/reporting), no a tiempo real. Ideal para complementar el dashboard con métricas de portfolio que actualmente no se calculan.

---

### 1.7 stocksight

| | |
|---|---|
| **Repositorio** | https://github.com/shirosaidev/stocksight |
| **Stars** | ~2.000+ |
| **Licencia** | Apache 2.0 |
| **Lenguaje** | Python |
| **Estado** | Mantenimiento reducido |

**Descripción**: Herramienta de análisis bursátil que combina procesamiento de lenguaje natural (NLP) con análisis de sentimiento. Recopila noticias y tweets, analiza su sentimiento y almacena los resultados en Elasticsearch para visualización y análisis.

**Funcionalidades principales**:
- Ingesta de noticias financieras y tweets sobre activos.
- Análisis de sentimiento mediante NLP.
- Almacenamiento indexado en Elasticsearch.
- Visualización mediante Kibana.
- Correlación sentimiento ↔ precio.

**Aplicación en InvestAIlert**:
- **Referencia arquitectónica**: Su arquitectura (noticias → NLP → sentiment → almacenamiento → visualización) es muy similar a la de InvestAIlert. Sirve como punto de comparación para validar decisiones de diseño.
- **Ideas de funcionalidades**: Su sistema de correlación sentimiento/precio podría inspirar funcionalidades futuras.

**Consideraciones**: El proyecto tiene mantenimiento reducido y usa tecnologías más antiguas (Elasticsearch/Kibana). Su valor principal para nosotros es como referencia conceptual, no para integración directa de código.

---

### 1.8 alpha_vantage (wrapper Python)

| | |
|---|---|
| **Repositorio** | https://github.com/RomelTorres/alpha_vantage |
| **Stars** | ~4.000+ |
| **Licencia** | MIT |
| **Lenguaje** | Python |
| **Estado** | Mantenimiento activo |

**Descripción**: Wrapper Python oficial para la API de Alpha Vantage. Proporciona acceso a datos de mercado, fundamentales, indicadores técnicos, divisas y criptomonedas.

**Funcionalidades principales**:
- Datos históricos y en tiempo real de precios.
- Indicadores técnicos (SMA, EMA, RSI, MACD, Bollinger, etc.).
- Datos fundamentales (income statement, balance sheet, cash flow).
- Datos de divisas y criptomonedas.
- Búsqueda de símbolos.

**Aplicación en InvestAIlert**:
- **Ya parcialmente integrado**: Nuestro módulo `modules/ingestion/alphavantage.py` implementa llamadas directas a la API. Podríamos refactorizar para usar este wrapper oficial, que maneja paginación, rate limiting y errores de forma más robusta.
- **Indicadores técnicos**: Acceder a indicadores técnicos pre-calculados sin necesidad de librerías adicionales.

**Consideraciones**: Requiere API key (plan gratuito: 25 requests/día). Actualmente tenemos `ALPHAVANTAGE_KEY=` vacío en `.env`. La integración sería útil solo si se configura una key.

---

### 1.9 yahooquery

| | |
|---|---|
| **Repositorio** | https://github.com/dpguthrie/yahooquery |
| **Stars** | ~1.000+ |
| **Licencia** | MIT |
| **Lenguaje** | Python |
| **Estado** | Activo |

**Descripción**: Wrapper alternativo para Yahoo Finance con énfasis en datos fundamentales, ESG, análisis de consenso de analistas y datos institucionales. Complementa a yfinance con algunos endpoints adicionales.

**Funcionalidades principales**:
- Datos fundamentales detallados (income statement, balance sheet, cash flow).
- Datos ESG (Environmental, Social, Governance scores).
- Consenso de analistas (price targets, recomendaciones).
- Datos de ownership institucional y de insiders.
- Trending tickers y market movers.

**Aplicación en InvestAIlert**:
- **Alternativa/complemento a yfinance**: Más estable para datos fundamentales detallados.
- **Datos ESG**: Añadir scoring ESG a los activos de la cartera (relevante para inversión sostenible).
- **Consenso de analistas**: Enriquecer alertas con el consenso de analistas (target price, buy/sell/hold).

**Consideraciones**: Funcionalidad similar a yfinance en muchos aspectos. La elección entre ambas depende de los endpoints específicos necesarios. Pueden coexistir sin conflicto.

---

## 2. Herramientas de interés general (fuera de scope actual)

Estas herramientas son relevantes para el ecosistema de inversiones pero no aplican directamente a un sistema de alertas basado en noticias. Podrían ser útiles en evoluciones futuras o proyectos complementarios.

---

### 2.1 FinRL — Financial Reinforcement Learning

| | |
|---|---|
| **Repositorio** | https://github.com/AI4Finance-Foundation/FinRL |
| **Stars** | ~14.800 |
| **Licencia** | MIT |
| **Lenguaje** | Python (PyTorch, Stable Baselines 3) |

**Descripción**: Framework de referencia para aplicar Deep Reinforcement Learning (DRL) al trading cuantitativo. Soporta múltiples algoritmos (A2C, DDPG, PPO, SAC, TD3), 14+ fuentes de datos y múltiples entornos de mercado. Recientemente evolucionó a FinRL-X con arquitectura modular para producción.

**Por qué no aplica ahora**: InvestAIlert es un sistema de monitorización y alertas, no ejecuta operaciones de trading. FinRL está diseñado para entrenar agentes que toman decisiones de compra/venta autónomas.

**Potencial futuro**: Si el proyecto evolucionara hacia un "robo-advisor" que sugiere acciones concretas (comprar/vender/mantener) basadas en alertas, FinRL podría entrenar el agente decisor.

---

### 2.2 backtesting.py

| | |
|---|---|
| **Repositorio** | https://github.com/kernc/backtesting.py |
| **Stars** | ~6.000+ |
| **Licencia** | AGPL-3.0 |
| **Lenguaje** | Python |

**Descripción**: Framework ligero para backtesting de estrategias de trading. Permite definir estrategias con indicadores técnicos y ejecutarlas sobre datos históricos para evaluar rendimiento.

**Por qué no aplica ahora**: No definimos ni evaluamos estrategias de trading. Nuestro sistema detecta eventos y genera alertas, no ejecuta ni simula operaciones.

**Potencial futuro**: Podría usarse para validar retrospectivamente si las alertas generadas por InvestAIlert habrían sido accionables (meta-backtesting de la calidad de las alertas).

---

### 2.3 vectorbt

| | |
|---|---|
| **Repositorio** | https://github.com/polakowo/vectorbt |
| **Stars** | ~5.000+ |
| **Licencia** | Custom (vectorbt PRO es comercial) |
| **Lenguaje** | Python (NumPy vectorizado) |

**Descripción**: Motor de backtesting de alta velocidad basado en operaciones vectorizadas con NumPy. Permite analizar miles de combinaciones de estrategias en segundos.

**Por qué no aplica ahora**: Mismo motivo que backtesting.py — orientado a backtesting de estrategias de trading, no a alertas.

---

### 2.4 Qlib (Microsoft)

| | |
|---|---|
| **Repositorio** | https://github.com/microsoft/qlib |
| **Stars** | ~17.000+ |
| **Licencia** | MIT |
| **Lenguaje** | Python |

**Descripción**: Plataforma de investigación cuantitativa con IA desarrollada por Microsoft Research. Incluye pipeline completo de datos, modelos predictivos, backtesting y análisis de portfolios. Soporta modelos avanzados de ML/DL para predicción de precios.

**Por qué no aplica ahora**: Es una plataforma de investigación cuantitativa completa, orientada a predicción de precios y optimización de portfolios. Excede ampliamente el scope de un sistema de alertas informativas.

**Potencial futuro**: Los modelos predictivos de Qlib podrían alimentar un módulo de "predicción de impacto" más sofisticado que las estimaciones deterministas actuales.

---

### 2.5 pybroker

| | |
|---|---|
| **Repositorio** | https://github.com/edtechre/pybroker |
| **Stars** | ~2.000+ |
| **Licencia** | Apache 2.0 |
| **Lenguaje** | Python |

**Descripción**: Framework de trading algorítmico que integra Machine Learning para construir, probar y desplegar estrategias de trading. Soporta indicadores personalizados, modelos ML y simulación realista con comisiones y slippage.

**Por qué no aplica ahora**: Trading algorítmico y ejecución de órdenes — fuera del scope de alertas informativas.

---

### 2.6 Blankly

| | |
|---|---|
| **Repositorio** | https://github.com/blankly-finance/blankly |
| **Stars** | ~2.000+ |
| **Licencia** | LGPL-3.0 |
| **Lenguaje** | Python |

**Descripción**: Framework para construir, backtestear y desplegar bots de trading multi-exchange (Alpaca, Coinbase, Binance, etc.). Enfocado en simplificar el ciclo de vida completo de un bot de trading.

**Por qué no aplica ahora**: Bots de trading automatizado — completamente diferente a monitorización de noticias.

---

### 2.7 TradingAgents

| | |
|---|---|
| **Repositorio** | https://github.com/TauricResearch/TradingAgents |
| **Stars** | ~5.000+ |
| **Licencia** | MIT |
| **Lenguaje** | Python |

**Descripción**: Framework multi-agente basado en LLMs para trading financiero. Simula un equipo de analistas (fundamental, técnico, sentimiento) que debaten y llegan a decisiones de trading consensuadas.

**Por qué no aplica ahora**: Aunque usa LLMs y análisis de sentimiento (similar a InvestAIlert), su objetivo final es ejecutar trades, no generar alertas informativas.

**Potencial futuro**: Su arquitectura multi-agente podría inspirar una evolución de InvestAIlert donde múltiples "especialistas" (macro, técnico, fundamental, sentimiento) contribuyen a la evaluación de cada alerta.

---

### 2.8 vnpy

| | |
|---|---|
| **Repositorio** | https://github.com/vnpy/vnpy |
| **Stars** | ~26.000+ |
| **Licencia** | MIT |
| **Lenguaje** | Python |

**Descripción**: Plataforma de trading cuantitativo desarrollada por la comunidad china. Soporta múltiples exchanges (chinos e internacionales), estrategias algorítmicas, backtesting y ejecución en producción.

**Por qué no aplica ahora**: Orientada a ejecución de órdenes en mercados, principalmente chinos. Diferente propósito y mercado objetivo.

---

### 2.9 FinQuant

| | |
|---|---|
| **Repositorio** | https://github.com/fmilthaler/FinQuant |
| **Stars** | ~1.000+ |
| **Licencia** | MIT |
| **Lenguaje** | Python |

**Descripción**: Librería de optimización y análisis de portfolios. Implementa optimización de Markowitz (mean-variance), simulación de Monte Carlo, frontera eficiente y análisis de componentes principales (PCA) para portfolios.

**Por qué no aplica ahora**: Optimización de pesos de cartera — nuestro sistema no recomienda distribución de activos, solo alerta sobre eventos.

**Potencial futuro**: Podría integrarse en un Tier 4 para sugerir rebalanceos de cartera cuando las alertas indiquen cambios significativos en el perfil de riesgo.

---

### 2.10 mplfinance

| | |
|---|---|
| **Repositorio** | https://github.com/matplotlib/mplfinance |
| **Stars** | ~4.000+ |
| **Licencia** | BSD-3 |
| **Lenguaje** | Python (Matplotlib) |

**Descripción**: Librería de visualización financiera basada en Matplotlib. Genera gráficos de velas (candlestick), OHLC, Renko, Point & Figure con indicadores técnicos superpuestos.

**Por qué no aplica ahora**: Nuestro frontend usa React con Recharts para visualización. Los gráficos Python de mplfinance serían redundantes. Sería útil solo si generáramos reportes PDF desde el backend.

---

### 2.11 PatternPy

| | |
|---|---|
| **Repositorio** | https://github.com/keithorange/PatternPy |
| **Stars** | ~1.000+ |
| **Licencia** | MIT |
| **Lenguaje** | Python |

**Descripción**: Librería de reconocimiento automático de patrones técnicos en gráficos de precios (head & shoulders, double top/bottom, triangles, wedges, etc.).

**Por qué no aplica ahora**: Análisis técnico de patrones de precios — nuestro sistema se basa en análisis de noticias y eventos, no en chartismo.

---

### 2.12 EigenLedger

| | |
|---|---|
| **Repositorio** | https://github.com/santoshlite/EigenLedger |
| **Stars** | ~1.000+ |
| **Licencia** | MIT |
| **Lenguaje** | Python |

**Descripción**: Motor de backtesting de portfolios. Permite evaluar el rendimiento histórico de diferentes configuraciones de cartera con métricas de riesgo y rendimiento.

**Por qué no aplica ahora**: Backtesting de portfolios estáticos — no tiene relación con monitorización de noticias en tiempo real.

---

## 3. Resumen comparativo

### Prioridad de integración en InvestAIlert

| Prioridad | Herramienta | Esfuerzo | Impacto | Descripción corta |
|---|---|---|---|---|
| ✅ Integrado | **yfinance** | Bajo | Alto | Auto-fill de activos + datos de mercado + histórico OHLCV |
| ✅ Integrado | **quantstats** | Bajo | Medio | Métricas de rendimiento/riesgo de cartera en dashboard |
| 🔴 Alta | **FinGPT** | Medio | Alto | Sentiment analysis superior a FinBERT |
| 🟡 Media | **FinanceDatabase** | Bajo | Medio | Lookup offline de metadatos de activos |
| 🟡 Media | **FinanceToolkit** | Medio | Medio | Ratios financieros y análisis fundamental |
| 🟢 Baja | **OpenBB** | Alto | Alto | Capa de datos unificada (posible refactor grande) |
| 🟢 Baja | **yahooquery** | Bajo | Bajo | Complemento de yfinance para ESG/analistas |
| 🟢 Baja | **alpha_vantage** | Bajo | Bajo | Refactor de integración existente |
| ⚪ Referencia | **stocksight** | — | — | Validación arquitectónica |

### Mapa de categorías

```
┌─────────────────────────────────────────────────────────────┐
│                    ECOSISTEMA INVERSIONES                    │
├────────────────────┬────────────────────────────────────────┤
│   DATOS MERCADO    │  yfinance, OpenBB, FinanceDatabase,    │
│                    │  yahooquery, alpha_vantage              │
├────────────────────┼────────────────────────────────────────┤
│   NLP / LLM        │  FinGPT, stocksight                   │
│   FINANCIERO       │                                        │
├────────────────────┼────────────────────────────────────────┤
│   ANÁLISIS         │  FinanceToolkit, quantstats,           │
│   PORTFOLIO        │  FinQuant, EigenLedger                 │
├────────────────────┼────────────────────────────────────────┤
│   TRADING          │  FinRL, pybroker, Blankly, vnpy,       │
│   ALGORÍTMICO      │  TradingAgents                         │
├────────────────────┼────────────────────────────────────────┤
│   BACKTESTING      │  backtesting.py, vectorbt              │
├────────────────────┼────────────────────────────────────────┤
│   VISUALIZACIÓN    │  mplfinance, PatternPy                 │
├────────────────────┼────────────────────────────────────────┤
│   QUANT RESEARCH   │  Qlib (Microsoft)                      │
└────────────────────┴────────────────────────────────────────┘
```

---

> **Nota**: Todas las herramientas listadas son open-source con licencias permisivas (MIT, Apache 2.0, BSD) salvo OpenBB (AGPL-3.0), Blankly (LGPL-3.0) y backtesting.py (AGPL-3.0). Para un TFM académico, todas las licencias son compatibles.
