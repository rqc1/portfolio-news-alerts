# Guía de Despliegue Gratuito – InvestAIlert

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
git remote add origin https://github.com/TU_USUARIO/investailert.git
git push -u origin main
```

> Crear un archivo `.gitignore` si no existe:
> ```
> __pycache__/
> .env
> .next/
> node_modules/
> *.pyc
> ```

---

## Paso 2: Deploy Backend en Render

1. Ve a [render.com](https://render.com) → Sign up (gratis con GitHub)
2. **New → Web Service** → conecta tu repo de GitHub
3. Configuración:
   - **Name**: `investailert-api`
   - **Root Directory**: (dejar vacío, es la raíz)
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements-cloud.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: Free

4. **Environment Variables** (en el dashboard de Render):
   ```
   CLOUD_MODE=true
   LLM_PROVIDER=github
   GITHUB_TOKEN=ghp_xxxxx
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
   CRON_SECRET=mi_token_secreto_12345
   ```

5. Click **Create Web Service** → espera ~2 min a que despliegue
6. Tu API estará en: `https://investailert-api.onrender.com`

---

## Paso 3: Deploy Frontend en Vercel

1. Ve a [vercel.com](https://vercel.com) → Sign up (gratis con GitHub)
2. **New Project** → importa tu repo
3. Configuración:
   - **Framework**: Next.js (autodetectado)
   - **Root Directory**: `frontend`
4. **Environment Variables**:
   ```
   NEXT_PUBLIC_API_BASE_URL=https://investailert-api.onrender.com
   ```
5. Click **Deploy** → ~1 min
6. Tu frontend estará en: `https://investailert.vercel.app` (o similar)

---

## Paso 4: Configurar Cron Diario (cron-job.org)

1. Ve a [cron-job.org](https://cron-job.org) → Sign up gratis
2. **Create Cron Job**:
   - **URL**: `https://investailert-api.onrender.com/api/trigger-pipeline?token=mi_token_secreto_12345`
   - **Method**: POST
   - **Schedule**: Every day at 08:00 (o la hora que prefieras)
   - **Timezone**: Europe/Madrid
3. Save

Esto despertará el backend (Render free tier duerme tras 15 min de inactividad), ejecutará el pipeline completo (ingestar RSS → procesar alertas → enviar emails) y luego el servicio volverá a dormir.

---

## Paso 5: Verificar que funciona

1. Espera a que el cron se ejecute, o fuerza manualmente:
   ```bash
   curl -X POST "https://investailert-api.onrender.com/api/trigger-pipeline?token=mi_token_secreto_12345"
   ```
2. Revisa tu email (`ruben.querol.c@gmail.com`) para alertas
3. Visita el frontend para ver el dashboard

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
