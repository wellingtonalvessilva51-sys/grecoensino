# syntax=docker/dockerfile:1

# --- Stage 1: build do front (Vite + React) ---
FROM node:20-bookworm-slim AS front
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
# Front genérico: a config de runtime (tenant/API) vem do window.__ENV__
# injetado pelo backend. Não precisa de VITE_* aqui.
RUN npm run build

# --- Stage 2: runtime do backend (FastAPI) que serve o front ---
FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY alembic.ini ./
COPY migrations/ ./migrations/
COPY scripts/ ./scripts/
COPY src/ ./src/
# Build do front no local esperado por src/main.py (web/dist).
COPY --from=front /web/dist ./web/dist

RUN chmod +x ./scripts/entrypoint.sh

EXPOSE 8000
# Migrations → bootstrap/seed condicional → uvicorn (ver scripts/entrypoint.sh).
# O seed demo só roda com ALLOW_DEMO_SEED=true: um deploy real nunca recria
# usuários de vitrine com senha conhecida.
CMD ["./scripts/entrypoint.sh"]
