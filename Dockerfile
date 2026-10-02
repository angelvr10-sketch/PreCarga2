# ── Stage 1: build del frontend React ──────────────────────────
FROM node:22-slim AS frontend

WORKDIR /build

# Se copian primero los manifiestos para que la capa de npm ci
# se cachee mientras no cambien las dependencias.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build


# ── Stage 2: runtime Python ────────────────────────────────────
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Artefactos del build de React ( Stage 1 )
COPY --from=frontend /build/dist ./frontend/dist

# Precompila bytecode para no pagar la compilacion en cada cold start.
RUN python -m compileall -q /app

EXPOSE 8080

# --workers: los handlers hacen I/O bloqueante, con 1 solo proceso
# FastAPI atiende una peticion a la vez.
CMD ["uvicorn", "main:app", \
     "--host", "0.0.0.0", \
     "--port", "8080", \
     "--workers", "2", \
     "--proxy-headers", \
     "--forwarded-allow-ips", "*"]
