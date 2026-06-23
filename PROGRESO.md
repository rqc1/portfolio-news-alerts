# InvestAIlert – Progreso y Decisiones

**Proyecto:** TFE – Sistema inteligente de alertas por noticias para carteras de inversión  
**Autor:** Rubén Querol  
**Inicio:** Mayo 2026

---

## Estado Actual

| Componente | Estado | Notas |
|---|---|---|
| Cartera persistente (MongoDB Atlas) | ✅ Operativo | 9 activos configurados |
| Ingesta RSS (30+ fuentes) | ✅ Operativo | Reuters, Yahoo, FT, CNBC, prensa española... |
| Pipeline NLP (NER, limpieza, idioma) | ✅ Operativo | spaCy + detección/traducción |
| Clasificación de eventos (NLI) | ✅ Operativo | BART zero-shot + FinBERT sentiment |
| Motor de alertas (relevancia + impacto) | ✅ Operativo | Reglas + semántica + LLM borderline |
| Análisis contextual LLM | ✅ Operativo | GitHub Models (GPT-4.1-mini) |
| Deduplicación semántica | ✅ Operativo | Sentence-transformers |
| Notificaciones email | ✅ Operativo | Gmail SMTP (App Password configurada) |
| Scheduler (1x/día) | ✅ Configurado | Ingesta + alertas cada 24h |
| Frontend Next.js | ✅ Funcional | Dashboard de alertas |
| Evaluación (ablación + IAA) | ✅ Operativo | 4 variantes + acuerdo inter-anotador (α=0,91) |
| Validación financiera (event study) | ✅ Operativo | AR/CAR + backtesting + autocalibración |
| Calibración de severidad + guardrails LLM | ✅ Operativo | `modules/impact/calibration.py` |
| Resolución canónica de entidades | ✅ Operativo | `modules/nlp/entity_resolver.py` |
| Capa de producción (JWT, logs, métricas) | ✅ Operativo | `modules/security/` + rate limit + CORS + health |

---

## Cartera Configurada

| Ticker | Empresa | Sector | País |
|---|---|---|---|
| MSFT | Microsoft Corporation | Technology | US |
| V | Visa Inc. | Financial Services | US |
| TLN.MC | Talgo S.A. | Industrials | ES |
| KAP.L | Kapital VCT plc | Financial Services | GB |
| NVDA | NVIDIA Corporation | Technology | US |
| TSM | Taiwan Semiconductor Manufacturing | Technology | TW |
| NU | Nu Holdings Ltd. | Financial Services | BR |
| AMD | Advanced Micro Devices Inc. | Technology | US |
| AVGO | Broadcom Inc. | Technology | US |

---

## Decisiones Tomadas

### 1. Frecuencia del scheduler: 1 vez al día
- **Decisión:** Cambiar de cada 15-20 min a cada 24 horas.
- **Razón:** Para uso personal es suficiente un análisis diario. Reduce consumo de recursos y llamadas a APIs.
- **Config:** `SCHEDULER_INGEST_INTERVAL_MIN=1440`, `SCHEDULER_ALERTS_INTERVAL_MIN=1440`

### 2. LLM Provider: GitHub Models (gratuito)
- **Decisión:** Usar GitHub Models con `GITHUB_TOKEN` existente.
- **Modelo:** GPT-4.1-mini vía endpoint de GitHub.
- **Razón:** Gratuito, suficiente calidad para análisis de impacto y explicaciones.

### 3. MongoDB Atlas (Free Tier)
- **Decisión:** Usar cluster gratuito en Atlas en lugar de MongoDB local.
- **Razón:** Persistencia en la nube, accesible desde cualquier sitio, 512 MB gratis.

### 4. Email vía Gmail SMTP
- **Decisión:** Usar cuenta personal Gmail con App Password.
- **Pendiente:** Crear la App Password (requiere 2FA activo).

### 5. Consolidación de carteras
- **Decisión:** Eliminar la cartera vieja de validación (3 activos) y mantener solo la de 9 activos.
- **Razón:** Evitar procesamiento duplicado.

### 6. Endurecimiento técnico (7 debilidades subsanadas)
- **Decisión:** Resolver al máximo nivel las 7 debilidades concretas del sistema antes del cierre del TFM.
- **Alcance:**
  - (a) Calibración de severidad + guardarraíles deterministas sobre la salida del LLM (`modules/impact/`).
  - (b) Estudio de evento (AR/CAR, MacKinlay 1997) + backtesting (`modules/backtest/`).
  - (c) Acuerdo inter-anotador: κ de Cohen, κ ponderado, α de Krippendorff (`evaluation/agreement.py`).
  - (d) Relevancia semántica por activo (`modules/relevance/`).
  - (e) Resolución canónica de entidades (`modules/nlp/entity_resolver.py`).
  - (f) Bucle de retroalimentación + autocalibración de umbrales (`/api/backtest/{id}/calibrate`).
  - (g) Capa de producción: JWT, logging estructurado, métricas Prometheus, rate limiting, CORS, health probes (`modules/security/`).
- **Resultado:** +200 tests verdes. Ablación completa de 4 variantes documentada en el TFM. Ver detalle en [`NOTAS_TECNICAS.md`](NOTAS_TECNICAS.md) §6.

### 7. Autenticación: bcrypt directo (no passlib)
- **Decisión:** Usar la librería `bcrypt` directamente en lugar de `passlib`.
- **Razón:** `passlib 1.7.4` es incompatible con `bcrypt 5.0.0`. Se trunca la contraseña a 72 bytes UTF-8 explícitamente.
- **`AUTH_ENABLED` por defecto `false`** para preservar compatibilidad con frontend y tests (degradación elegante).

---

## Pendiente

- [x] Crear Gmail App Password y configurar en `.env`
- [x] Verificar envío de email real con alerta
- [x] Documentar métricas de evaluación del sistema (precision, recall de alertas)
- [x] Subsanar las 7 debilidades técnicas (ver Decisión 6)
- [x] Documentar el endurecimiento técnico en el TFM y en los docs del proyecto
- [ ] Considerar añadir horario fijo (ej: 8:00 UTC) en vez de intervalo de 24h
- [ ] Evaluar si añadir más fuentes RSS específicas para los activos de la cartera
- [ ] Desplegar el servidor en producción (o ejecutar localmente de forma persistente)

---

## Historial de Cambios

| Fecha | Cambio |
|---|---|
| 2026-05-07 | Cartera de 9 activos creada en MongoDB Atlas |
| 2026-05-07 | SMTP configurado en .env (pendiente App Password) |
| 2026-05-07 | Scheduler ajustado a 1x/día (1440 min) |
| 2026-05-07 | Test e2e exitoso: alerta generada para noticia de NVIDIA (severidad muy_alta, alcista) |
| 2026-05-07 | Verificado: pipeline detecta impacto indirecto (NVDA → TSM por cadena de suministro) |
| 2026-05-14 | App Password configurada (rubenquerolcervantes@gmail.com) — email funciona ✅ |
| 2026-05-14 | Pipeline ejecutado: 451 noticias ingeridas, 4 alertas reales generadas |
| 2026-05-14 | Alertas reales: Cerebras IPO (TSM), Microsoft-OpenAI (MSFT), Ciberataques AI (TSM), Regulación minería (AMD) |
| 2026-06-03 | **Comparación multi-modelo LLM (v2.0):** 7 modelos evaluados con 10 noticias (580.1s, exit code 0). Phi-4 y Phi-4-reasoning descartados en v1.0 por timeouts/JSON inválido. GPT-4o mejor overall (0 errores, conf 0.815, 2.8s). Llama-3.1-8B más rápido (1.7s). DeepSeek-V3/R1 competitivos pero afectados por rate limiting (2/10 errores 429). Resultados en `evaluation/results/model_comparison_report.json` y `scripts/model_comparison_results.json`. |
| 2026-06-XX | **Endurecimiento técnico (7 debilidades):** calibración de severidad + guardrails LLM, event study (AR/CAR) + backtesting, acuerdo inter-anotador (κ Cohen / κ ponderado / α Krippendorff), relevancia semántica por activo, resolución canónica de entidades, bucle de retroalimentación, capa de producción (JWT/logs/métricas/rate-limit/CORS/health). +200 tests verdes. |
| 2026-06-XX | **Ablación completa:** 4 variantes evaluadas (reglas/híbrida/híbrida+NLI/completa). Híbrida+NLI: evento F1 macro 0,735, dirección 0,926, severidad MAE 0,593. Resultados en `evaluation/results/ablation_summary.json`. |
| 2026-06-XX | **Documentación:** TFM (cap. 4 y 5) regenerado con IAA, ablación, calibración, event study, bucle de retroalimentación y capa de producción. Actualizados `NOTAS_TECNICAS.md`, `PROGRESO.md` y READMEs de módulos. |
| 2026-06-11 | **Registro experimental:** creado [`RESULTADOS_EXPERIMENTALES.md`](RESULTADOS_EXPERIMENTALES.md) con histórico fechado de todas las ejecuciones (ablación, IAA, comparación multi-modelo, pipeline diario). `daily_pipeline.py` y `compare_models.py` ahora vuelcan resultados automáticamente a este documento. |
| 2026-06-11 | **Pipeline diario (cartera real):** ingesta RSS=457 + SEC=4, 100 noticias procesadas → 5 alertas (MSFT BitLocker, CaixaBank→V/NU, MSFT Exchange, D-Matrix→MSFT/NVDA, FreightWaves→AMD). BD: noticias 2479→2940, alertas 31→36. Corregido `PORTFOLIO_ID` antiguo; ingesta dinámica desde `portfolio.get_tickers()`. |
| 2026-06-11 | **Comparación multi-modelo LLM:** 7 modelos × 8 noticias relevantes (471.8s). GPT-4o y DeepSeek-V3 más conservadores (mayoría neutral); Llama-3.1-8B más decisivo y rápido (~2s); Llama-3.3-70B con 2 fallos de parseo JSON. Detalle en `RESULTADOS_EXPERIMENTALES.md`. |
