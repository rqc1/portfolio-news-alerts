# Guía de Despliegue Gratuito – InvestAIlert

## Resumen del Despliegue Realizado

| Componente | Servicio | URL |
|---|---|---|
| **Backend API** | Render (Free) | https://portfolio-news-alerts.onrender.com |
| **Frontend** | Vercel (Free) | https://frontend-blue-nine-yzzmh0b8j8.vercel.app |
| **Base de datos** | MongoDB Atlas (M0 Free) | clusteinvesailert.gniynvm.mongodb.net |
| **LLM** | GitHub Models | Via GITHUB_TOKEN |
| **Cron diario** | cron-job.org (Free) | POST cada día a las 08:00 |
| **Repo GitHub** | GitHub | https://github.com/rqc1/portfolio-news-alerts |

**RAM del backend**: ~150MB (vs ~2GB con modelos ML locales)

---

## Arquitectura Cloud (100% Gratis)

| Componente | Servicio | Plan |
|---|---|---|
| **Backend API** | [Render](https://render.com) | Free |
| **Frontend** | [Vercel](https://vercel.com) | Free |
| **Base de datos** | MongoDB Atlas | Free (M0) |
| **LLM** | GitHub Models | Free (GITHUB_TOKEN) |
| **Cron diario** | [cron-job.org](https://cron-job.org) | Free |

**RAM estimada del backend**: ~150MB (vs ~2GB con modelos ML locales)

---

## Paso 1: Subir código a GitHub

```bash
cd c:\Users\rquerol\Documents\UNIR\TFE
git init
git add .
git commit -m "Initial: InvestAIlert full stack"
git remote add origin https://github.com/rqc1/portfolio-news-alerts.git
git push -u origin main
```

> El archivo `.gitignore` excluye `.env`, `node_modules/`, `.next/`, `__pycache__/`

---

## Paso 2: Deploy Backend en Render (Docker)

1. Ve a [render.com](https://render.com) → Sign up (gratis con GitHub)
2. **New → Web Service** → conecta el repo `rqc1/portfolio-news-alerts`
3. Render detecta el `Dockerfile` automáticamente
4. Configuración:
   - **Name**: `portfolio-news-alerts`
   - **Branch**: `main`
   - **Root Directory**: (vacío)
   - **Runtime**: Docker (autodetectado por Dockerfile)
   - **Docker Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: Free

4. **Environment Variables** (en el dashboard de Render → Environment):
   ```
   CLOUD_MODE=true
   LLM_PROVIDER=github
   GITHUB_TOKEN=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
   MONGO_URI=mongodb+srv://ruben:ruben@clusteinvesailert.gniynvm.mongodb.net/
   MONGO_DB_NAME=portfolio_alerts
   NOTIFICATIONS_ENABLED=true
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USE_TLS=true
   SMTP_USER=rubenquerolcervantes@gmail.com
   SMTP_PASSWORD=xurlqvzoafpwbfca
   SMTP_FROM=rubenquerolcervantes@gmail.com
   NOTIFICATION_EMAIL_TO=ruben.querol.c@gmail.com
   CRON_SECRET=investailert2026secret
   ```

5. **MongoDB Atlas** → Network Access → Add IP `0.0.0.0/0` (necesario para Render free, IP dinámica)
6. Click **Deploy** → espera ~5 min para build Docker
7. URL resultante: `https://portfolio-news-alerts.onrender.com`

---

## Paso 3: Deploy Frontend en Vercel (CLI)

El frontend se desplegó con Vercel CLI (deploy manual, sin vincular repo):

```bash
npm i -g vercel
cd frontend
vercel login          # Login con email (abre navegador)
vercel env add NEXT_PUBLIC_API_BASE_URL production
# Valor: https://portfolio-news-alerts.onrender.com
vercel --prod --yes   # Deploy a producción
```

URL resultante: `https://frontend-blue-nine-yzzmh0b8j8.vercel.app`

**Environment Variables configuradas en Vercel:**
```
NEXT_PUBLIC_API_BASE_URL=https://portfolio-news-alerts.onrender.com
```

---

## Paso 4: Configurar Cron Diario (cron-job.org)

1. Ve a [cron-job.org](https://cron-job.org) → Sign up gratis
2. **Create Cron Job**:
   - **URL**: `https://portfolio-news-alerts.onrender.com/api/trigger-pipeline?token=investailert2026secret`
   - **Method**: POST
   - **Schedule**: Every day at 08:00
   - **Timezone**: Europe/Madrid
3. Save

Esto despertará el backend (Render free tier duerme tras 15 min de inactividad), ejecutará el pipeline completo (ingestar RSS → procesar alertas → enviar emails) y luego el servicio volverá a dormir.

---

## Paso 5: Verificar que funciona

1. **Test rápido del backend** (esperar ~30s si está dormido):
   ```bash
   curl https://portfolio-news-alerts.onrender.com/api/system/status
   ```

2. **Trigger manual del pipeline**:
   ```bash
   curl -X POST "https://portfolio-news-alerts.onrender.com/api/trigger-pipeline?token=investailert2026secret"
   ```

3. Revisa email `ruben.querol.c@gmail.com` para las alertas

4. Visita el frontend: https://frontend-blue-nine-yzzmh0b8j8.vercel.app

---

## Notas Importantes

### Render Free Tier
- El servicio se **duerme** tras 15 min de inactividad
- La primera petición tras dormir tarda ~30-60 seg (cold start)
- El cron de cron-job.org despierta el servicio cada día
- Límite: 750 horas/mes (sobra para 1 servicio)

### CLOUD_MODE
- En cloud mode, el sistema usa **GitHub Models (LLM)** para:
  - Análisis de sentimiento (reemplaza FinBERT)
  - Clasificación de eventos (reemplaza BART NLI)
  - Relevancia semántica (reemplaza sentence-transformers)
- NLP básico (limpieza, detección idioma) se hace con regex
- **Resultado**: misma funcionalidad, 1/10 del uso de RAM

### Seguridad
- `CRON_SECRET` protege el endpoint de trigger contra ejecuciones no autorizadas
- Las env vars secretas se configuran en el dashboard de Render (no en el código)
- El `.env` local NO se sube a GitHub

---

## Arquitectura Visual

```
┌─────────────────────────────────────────────────────────┐
│                    USUARIO                                │
│                                                          │
│   ┌────────────┐              ┌────────────────┐        │
│   │  Frontend  │──── API ────▶│   Backend API  │        │
│   │  (Vercel)  │              │   (Render)     │        │
│   └────────────┘              └───────┬────────┘        │
│                                       │                  │
│                          ┌────────────┼────────────┐    │
│                          │            │            │    │
│                          ▼            ▼            ▼    │
│                    ┌──────────┐ ┌──────────┐ ┌────────┐│
│                    │ MongoDB  │ │ GitHub   │ │  Gmail  ││
│                    │  Atlas   │ │ Models   │ │  SMTP   ││
│                    └──────────┘ └──────────┘ └────────┘│
│                                                          │
│   ┌──────────────┐                                      │
│   │ cron-job.org │── POST /api/trigger-pipeline ────▶   │
│   │  (8:00 AM)   │                                      │
│   └──────────────┘                                      │
└─────────────────────────────────────────────────────────┘
```

---

## Cambios Técnicos Realizados para Cloud Deploy

### 1. CLOUD_MODE (`modules/cloud_mode.py`) — Módulo nuevo

Reemplaza modelos ML pesados (~2GB RAM) por llamadas a LLM vía API:

| Componente Local | Componente Cloud | Función |
|---|---|---|
| FinBERT (transformers) | `LLMSentiment` | Análisis de sentimiento |
| BART-NLI (zero-shot) | `LLMEventClassifier` | Clasificación de eventos |
| sentence-transformers | `LLMRelevanceScorer` | Scoring de relevancia |
| spaCy (en_core_web_sm) | `CloudNLPService` | Extracción de entidades (regex) |

**Activación**: `config.CLOUD_MODE = os.getenv("CLOUD_MODE", "false")` → env var en Render.

### 2. Dockerfile (modificado)

```dockerfile
FROM python:3.12-slim          # Cambiado de 3.13 (incompatibilidades numpy)
RUN apt-get install -y ca-certificates  # Certificados SSL para MongoDB Atlas
COPY requirements.txt .        # Solo dependencias ligeras (sin torch/transformers)
RUN pip install -r requirements.txt
# spaCy condicional: no falla si no está instalado
RUN python -c "import spacy; spacy.cli.download('en_core_web_sm')" 2>/dev/null || true
CMD ["python", "main.py"]
```

### 3. requirements.txt (reemplazado por versión cloud)

**Antes** (~2GB de dependencias): torch, transformers, sentence-transformers, spacy, etc.
**Ahora** (~50MB): fastapi, uvicorn, motor, httpx, openai, yfinance, pandas, etc.

El archivo original se conserva en `requirements-full.txt`.

### 4. database/mongodb.py (fix SSL Atlas)

```python
import certifi
# En connect():
kwargs["tlsCAFile"] = certifi.where()
```

**Problema**: Render Docker no tiene CA certs actualizados → `TLSV1_ALERT_INTERNAL_ERROR` al conectar a MongoDB Atlas.
**Solución**: Usar `certifi` para proporcionar el bundle de certificados raíz.

### 5. modules/relevance/service.py (lazy import)

```python
# ANTES (top-level, crasheaba en cloud):
from sentence_transformers import SentenceTransformer

# DESPUÉS (dentro de función):
def _load_embedding_model(self):
    from sentence_transformers import SentenceTransformer
    ...
```

### 6. modules/alerts/engine.py (import condicional)

```python
if config.CLOUD_MODE:
    from modules.cloud_mode import CloudNLPService, LLMSentiment, ...
else:
    from modules.nlp.preprocessing import NLPService  # Modelos pesados
```

### 7. main.py (skip preload en cloud)

```python
async def lifespan(app):
    if not config.CLOUD_MODE:
        await _preload_models()  # Solo carga modelos si no es cloud
```

Nuevo endpoint trigger:
```python
@app.post("/api/trigger-pipeline")
async def trigger_pipeline(token: str = Query(...)):
    if token != config.CRON_SECRET:
        raise HTTPException(403)
    # Ejecuta pipeline completo
```

### 8. Frontend TypeScript fix

```typescript
// frontend/src/app/advisor/page.tsx
disabled={!!(...)}  // Coerción bool (antes: boolean | null → error TS)
```

---

## Cómo Redesplegar

### Backend (automático)
```bash
git add . && git commit -m "fix: ..." && git push origin main
# Render detecta el push y redespliega automáticamente (~3 min)
```

### Frontend (manual con CLI)
```bash
cd frontend
vercel --prod --yes
```

---

## Portfolio Configurado

9 activos en MongoDB (colección `portfolios`):
- **Tech US**: MSFT, NVDA, TSM, AMD, AVGO
- **Fintech**: V, NU
- **España**: TLN.MC
- **UK**: KAP.L

---

## Costes

| Servicio | Plan | Límite |
|---|---|---|
| Render | Free | 750h/mes, auto-sleep 15min |
| Vercel | Hobby | 100GB bandwidth/mes |
| MongoDB Atlas | M0 | 512MB storage |
| GitHub Models | Free | Rate limited |
| cron-job.org | Free | 1 job/min resolución |
| **TOTAL** | **$0/mes** | |
