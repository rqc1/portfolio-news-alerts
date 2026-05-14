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
| Notificaciones email | ⚠️ Configurado, falta App Password | Gmail SMTP |
| Scheduler (1x/día) | ✅ Configurado | Ingesta + alertas cada 24h |
| Frontend Next.js | ✅ Funcional | Dashboard de alertas |

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

---

## Pendiente

- [x] Crear Gmail App Password y configurar en `.env`
- [x] Verificar envío de email real con alerta
- [ ] Considerar añadir horario fijo (ej: 8:00 UTC) en vez de intervalo de 24h
- [ ] Evaluar si añadir más fuentes RSS específicas para los activos de la cartera
- [ ] Documentar métricas de evaluación del sistema (precision, recall de alertas)
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
