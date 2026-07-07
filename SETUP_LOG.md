# Registro de Setup — gestão-educacional

> Log do que foi feito até agora. Última atualização: **2026-07-07**.
> Guia-fonte do projeto: `C:\Users\greco\Downloads\CLAUDE.md`.

## Ambiente instalado

| Ferramenta | Versão / Local |
|-----------|----------------|
| Python | 3.12 (user scope) — `C:\Users\greco\AppData\Local\Programs\Python\Python312` |
| Git | `C:\Program Files\Git\cmd` — configurado com `wellingtonalves.silva51@gmail.com` |
| venv do projeto | `C:\Users\greco\gestao-educacional\venv` |
| Docker Desktop | instalado via winget (`C:\Program Files\Docker\Docker\resources\bin\docker.exe`), client 29.6.1 |
| WSL2 | 2.7.10, kernel 6.18.33.2 — instalado 2026-07-07, reboot feito, **operacional** |
| PostgreSQL | container `gestao-postgres` (postgres:16), porta 5432, volume `gestao_pgdata`, DB `gestao_educacional` |

Instalações feitas via `winget`: `Python.Python.3.12`, `Git.Git`, `Docker.DockerDesktop`.

## Passos concluídos (commits no git)

```
7da51bf Passo 5: academico (estrutura curricular + matricula)
d031fd0 Passo 4: pessoas (cadastro + vinculos + ACL de responsavel)
8df8192 Passo 3: identidade (login/refresh/logout + RBAC + 403 estruturado)
815e0f6 Passo 2: multi-tenancy (resolucao + reforco na camada de dados)
e921032 Esqueleto inicial: app FastAPI + config + database + Alembic + healthcheck
```

**Passo 1 — Esqueleto:** app FastAPI (`src/main.py`), config (`src/core/config.py`),
database/SQLAlchemy (`src/core/database.py`), Alembic (`alembic.ini`, `migrations/`),
healthcheck, `requirements.txt`, `pyproject.toml`, `.gitignore`, `.env.example`, `README.md`.
Módulos criados: identidade, pessoas, academico, financeiro, comunicacao, tenancy.

**Passo 2 — Multi-tenancy:** `src/modules/tenancy/` (models/schemas/service),
`src/core/tenancy.py`, `src/core/tenant_guard.py`, migration `0001_criar_tabela_tenant.py`,
`scripts/seed_dev.py`, `tests/test_tenancy.py`.

**Passo 3 — Identidade:** login/refresh/logout + RBAC + 403 estruturado.
`src/modules/identidade/` (models/schemas/service/router), `src/core/security.py`,
migration `0002_criar_tabelas_identidade.py`, `tests/test_identidade.py`.

**Passo 4 — Pessoas:** cadastro + vínculos + ACL de responsável.
`src/modules/pessoas/` (models/schemas/service/router),
migration `0003_criar_tabelas_pessoas.py`, `tests/test_pessoas.py`.

**Passo 5 — Acadêmico:** estrutura curricular + matrícula.
`src/modules/academico/` (models/schemas/service/router),
migration `0004_criar_tabelas_academico.py`, `tests/test_academico.py`.

Testes (`pytest`) passando ao final de cada passo. Migrations 0001→0004 encadeadas.

## Setup do Docker/WSL2 (histórico do bloqueio)

1. Docker Desktop instalado, mas engine falhava: **"Virtualization support not detected"**.
2. Diagnóstico: virtualização **já habilitada no firmware** (VT-x/EPT ok na CPU i5-3470).
   Faltava o hypervisor do Windows → `bcdedit /set hypervisorlaunchtype auto` + **reboot** (feito).
3. Erro mudou para **500 Internal Server Error** no engine — virtualização destravou.
4. Causa do 500: **WSL2 não estava instalado** (wsl.exe era versão antiga inbox, sem kernel/distros).
5. Rodado elevado (ExitCode 0): `wsl --install --no-distribution` → instalou WSL 2.7.10 + kernel 6.18.
6. Recursos `VirtualMachinePlatform`/WSL ativados, mas exigem **REBOOT** (RebootPending=True,
   erro `WSL_E_WSL_OPTIONAL_COMPONENT_REQUIRED`).

## Ambiente de banco concluído (2026-07-07, após reboot)

Bloqueio Docker/WSL2 **resolvido**. Executado com sucesso:

1. Reboot feito → `wsl --status` e `wsl --version` OK (2.7.10), distro `docker-desktop` Running.
2. Docker Desktop com engine WSL2 no ar → `docker version` Server 29.6.1 respondendo.
3. Postgres subido: `docker run -d --name gestao-postgres -e POSTGRES_USER=postgres
   -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=gestao_educacional -p 5432:5432
   -v gestao_pgdata:/var/lib/postgresql/data postgres:16`.
4. `.env` criado a partir de `.env.example` (ignorado pelo git; `DATABASE_URL` aponta pro container).
5. `alembic upgrade head` → migrations 0001→0004 aplicadas.
6. `python -m scripts.seed_dev` → tenants demo (escola-a, escola-b) + admins
   (admin@escola-a.dev / admin@escola-b.dev, senha `admin12345`).
7. `pytest` → **36 passed**. Smoke test `GET /health` → 200 OK.

**Como religar o banco em nova sessão:** `docker start gestao-postgres` (o container e o
volume `gestao_pgdata` persistem; dados do seed continuam lá).

> Comandos usam o Python do venv: `.\venv\Scripts\python.exe -m alembic upgrade head`,
> `.\venv\Scripts\python.exe -m scripts.seed_dev`, `.\venv\Scripts\python.exe -m pytest`.

## Passo 6 — Notas e Frequência (núcleo de valor) — CONCLUÍDO

Entregue em 5 commits. Regras acadêmicas **configuráveis por escola** (§4), nunca
hardcoded. Migrations 0005→0008.

1. **Config acadêmica por tenant** (`config_academica`): `media_minima`,
   `num_periodos`, `pesos_periodos`, `frequencia_minima_percentual`. Defaults
   6,00 / 75%. Rotas `GET/PUT /academico/config`.
2. **Auditoria** (`auditoria_log`, append-only) em `core/audit.py` — §9.
3. **Frequência diária** (`frequencia`, por dia letivo): lançamento com ACL de
   docência; `frequencia-resumo` calcula % vs mínimo da escola.
4. **Notas** (`nota`, por período/disciplina): ACL fina por disciplina; período
   validado contra a config; grava auditoria em cada gravação.
5. **Boletim** (calculado on-the-fly): média anual ponderada pelos pesos →
   situação combinando média mínima E frequência mínima. `GET .../boletim`.

Testes: **72 passed**. Escopo adiado (confirmado com o usuário): recuperação/média
final e `boletim_fechamento` persistido. Arredondamento (2 casas HALF_UP) é default
**TODO: confirmar regra com a escola-piloto**.

## PRÓXIMO PASSO DE PRODUTO

Passo 7 do `CLAUDE.md`: **Financeiro básico** — título consolidado
(`titulo` 1→N `titulo_item`) + pagamento, pendentes/liquidados. Auditoria já pronta
para reuso. Consolidação de título (§4) **TODO: definir com a escola-piloto**.
