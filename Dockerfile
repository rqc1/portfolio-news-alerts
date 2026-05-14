# ---------- Stage 1: Build ----------
FROM python:3.12-slim AS builder

WORKDIR /app

# Instalar dependencias del sistema para compilar paquetes nativos
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---------- Stage 2: Runtime ----------
FROM python:3.12-slim

WORKDIR /app

# Copiar paquetes instalados desde builder
COPY --from=builder /install /usr/local

# Descargar modelo spaCy solo si está instalado (no en CLOUD_MODE)
RUN python -c "import spacy; spacy.cli.download('en_core_web_sm')" 2>/dev/null || true

# Copiar código fuente
COPY config.py main.py ./
COPY database/ database/
COPY modules/ modules/

# Pre-descargar modelos ML en build time (opción: comentar para descarga lazy)
# RUN python -c "from transformers import AutoTokenizer, AutoModelForSequenceClassification; AutoTokenizer.from_pretrained('ProsusAI/finbert'); AutoModelForSequenceClassification.from_pretrained('ProsusAI/finbert')"
# RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/system/status')" || exit 1

CMD ["python", "main.py"]
