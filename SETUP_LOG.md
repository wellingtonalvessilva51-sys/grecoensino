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

## Passo 7 — Financeiro básico — CONCLUÍDO

Entregue em 3 commits. Migrations 0009→0010. Regras alinhadas com o usuário.

1. **Título consolidado** (`titulo` 1→N `titulo_item`): valor_total somado no
   servidor; único por (aluno, competência) = "um título por vencimento" (§4);
   ACL: qualquer responsável vinculado vê; auditoria na criação.
2. **Pagamento parcial** (`pagamento`): status derivado pendente/parcial/liquidado;
   rejeita pagamento acima do saldo; auditoria; filtro por status.
3. **Gancho automático** (§6): `MatriculaCreate.cobranca_inicial` opcional →
   `financeiro.gerar_titulo_matricula` gera 1 título "MENSALIDADE" (idempotente por
   competência). Sem cobrança informada, não gera nada.

Decisões do usuário: criação manual + automática; pagamento parcial; ACL = qualquer
responsável vinculado; impor 1 título por aluno+competência; auto-geração usa valor
informado na matrícula (sem valor → não gera). Testes: **98 passed**.

Fora do MVP: app nunca trafega/armazena dado de cartão (só registro do pagamento;
gateway/PCI é fase futura). Recorrência de 12 mensalidades e valor por série ficaram
para depois.

## Passo 8 — Recados — CONCLUÍDO (fecha o MVP)

1 commit. Migration 0011. Módulo `comunicacao`.

- `recado` (autor_usuario_id, titulo, mensagem) + `recado_destinatario`
  (recado_id, pessoa_id, `lido_em`), único por (recado, pessoa).
- Envio: RBAC secretaria/professor/admin_tenant. Caixa de entrada por ACL
  (própria pessoa + dependentes). Marcar como lido (grava `lido_em`).
- `GET /recados` (inbox), `GET /recados/enviados` (autor),
  `POST /recados/destinatarios/{id}/lido`. Sem auditoria (§9 só Notas/Financeiro).
- 10 testes: RBAC, ACL de destinatário, duplicados, marcar lido, enviados.

## MVP COMPLETO (Passos 1–8)

Todos os passos do `CLAUDE.md` entregues. Suíte: **108 testes passando**.
Migrations 0001→0011. Módulos: identidade, pessoas, academico (+ notas,
frequência, boletim, config), financeiro (título consolidado + pagamento
parcial), comunicacao (recados). Multi-tenancy reforçado no guard, RBAC + ACL,
auditoria em Notas e Financeiro.

### Possíveis próximos passos (pós-MVP, a alinhar)
- Deploy no Railway (§5): variáveis de ambiente + Postgres gerenciado.
- Regras a fechar com a escola-piloto: arredondamento de média, recuperação/
  média final, recorrência de mensalidades (12x), valor por série.
- Gateway de pagamento (tokenização; PCI no provedor).

## Front web — EM ANDAMENTO (React + Vite + TS)

Framework: **React** (decidido com o usuário). 1ª fatia: **login + Portal do
Responsável**. Monorepo: pasta **`web/`**.

**Adiantado sem depender do Node (2026-07-09):**
- **CORS no backend**: `CORSMiddleware` em `src/main.py` (camada externa, trata
  preflight antes do tenant). Origens em `settings.cors_origins` (`CORS_ORIGINS`,
  default Vite dev). Validado por preflight (200, headers corretos). Suíte segue
  108 testes.
- **Scaffold `web/`**: Vite + React + TS. Cliente HTTP com refresh automático do
  JWT (`lib/api.ts`), contexto de auth (`lib/auth.tsx`), TanStack Query, guarda de
  rota, páginas Login e PortalResponsavel (consome matrículas, boletim,
  frequência-resumo, títulos, recados). Ainda **não rodado** (falta Node).

**BLOQUEIO:** Node.js não instalado. AÇÃO DO USUÁRIO: rodar via `!` no Claude Code
`! winget install OpenJS.NodeJS.LTS --accept-source-agreements --accept-package-agreements`
e aceitar o UAC (ou nodejs.org / nvm-windows). Depois: `cd web; npm install; npm run dev`.

**Ao retomar (depois do Node):** `npm install`; preencher `web/.env`
(`VITE_TENANT_ID` = UUID da escola-a do seed); criar um usuário **responsável**
demo com pessoa + vínculo + dados (estender `scripts/seed_dev.py`) para exercitar
o portal ponta a ponta; `npm run dev` e validar login → portal contra a API real.
