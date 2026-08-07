#!/bin/sh
# Entrypoint do container (Railway): migrations → bootstrap/seed → servidor.
#
# O seed demo NÃO roda por padrão: cria usuários com senha conhecida e só é
# liberado com ALLOW_DEMO_SEED=true. Para uma escola real, defina as variáveis
# BOOTSTRAP_* (ver DEPLOY_RAILWAY.md) e o admin é criado uma única vez.
set -e

echo "==> alembic upgrade head"
alembic upgrade head

if [ "$ALLOW_DEMO_SEED" = "true" ]; then
  echo "==> seed DEMO (ALLOW_DEMO_SEED=true) — senhas conhecidas, não use com dado real"
  python -m scripts.seed_dev
else
  echo "==> seed demo desligado"
fi

if [ -n "$BOOTSTRAP_ADMIN_EMAIL" ]; then
  echo "==> bootstrap da escola real (idempotente)"
  python -m scripts.bootstrap_prod
fi

echo "==> uvicorn na porta ${PORT:-8000}"
exec uvicorn src.main:app --host 0.0.0.0 --port "${PORT:-8000}"
