# Gestão Educacional (SaaS)

Monólito modular síncrono (FastAPI + SQLAlchemy 2 + PostgreSQL). Este repositório
começa pelo **esqueleto** (passo 1). Ver `CLAUDE.md` para escopo, regras de negócio
e ordem de implementação.

## Rodar em desenvolvimento

```bash
python -m venv venv
venv\Scripts\activate                 # Windows
pip install -r requirements.txt

copy .env.example .env                # e preencher os valores

alembic upgrade head                  # aplicar migrations (quando houver)
uvicorn src.main:app --reload         # sobe a API em http://127.0.0.1:8000

pytest                                # testes
```

- Healthcheck: `GET /health`
- Docs (Swagger): `GET /docs`

## Estrutura

```
src/
  main.py          # app FastAPI, middlewares e registro de routers
  core/            # config, database, security, tenancy, audit, exceptions
  shared/          # Base declarativa + mixins, dependências comuns
  modules/         # fatias de domínio (identidade, pessoas, academico, ...)
migrations/        # Alembic
tests/
```

Cada feature é entregue como **fatia vertical**: model → migration → schema →
service → router → teste.
