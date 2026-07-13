# Deploy no Railway (single-service, demo)

O deploy é **um único serviço**: o FastAPI serve a API (`/v1`) **e** o build do
front (SPA), na mesma URL. O tenant da escola é injetado no `index.html` em
runtime (`window.__ENV__`), então o front não precisa de rebuild por ambiente.

Já está tudo preparado no repositório:

- `Dockerfile` — multi-stage: builda o front (`web/`) e o embute no runtime do
  backend; o `CMD` roda `alembic upgrade head` → `seed_dev` → `uvicorn`.
- `railway.json` — builder DOCKERFILE + healthcheck em `/health`.
- `src/core/config.py` — normaliza a `DATABASE_URL` do Railway para psycopg3 e
  expõe a flag `ALLOW_TENANT_HEADER` e o `DEMO_TENANT_ID`.

> Validado localmente e via `docker build`/`docker run` contra Postgres.

## Passos (via GitHub — recomendado)

1. **Suba o repo para o GitHub** (crie o repositório remoto e faça push).
2. No **Railway**: *New Project → Deploy from GitHub repo* e selecione o repo.
   O Railway usa o `Dockerfile` (forçado pelo `railway.json`).
3. **Adicione o Postgres**: *New → Database → PostgreSQL*.
4. No serviço do backend, aba **Variables**, defina:
   | Variável | Valor |
   |---|---|
   | `DATABASE_URL` | referencie o Postgres: `${{Postgres.DATABASE_URL}}` |
   | `ENVIRONMENT` | `production` |
   | `ALLOW_TENANT_HEADER` | `true` |
   | `DEMO_TENANT_ID` | um UUID fixo (gere: `python -c "import uuid;print(uuid.uuid4())"`) |
   | `JWT_SECRET` | um segredo forte e aleatório |

   (O `PORT` é injetado pelo Railway automaticamente.)
5. **Deploy**. O container aplica migrations, semeia os dados demo e sobe.
   Healthcheck em `/health`.
6. **Gere o domínio**: *Settings → Networking → Generate Domain*.
7. Abra a URL. O tenant demo já vem injetado. Logins:
   - Responsável: `responsavel@escola-a.dev` / `resp12345`
   - Secretaria: `secretaria@escola-a.dev` / `sec12345`
   - Professor: `professor@escola-a.dev` / `prof12345`
   - Admin: `admin@escola-a.dev` / `admin12345`

## Alternativa — Railway CLI

```bash
npm i -g @railway/cli
railway login            # abre o navegador
railway init             # cria o projeto
railway add              # adicione o plugin PostgreSQL
railway up               # builda o Dockerfile e sobe
# defina as variáveis (mesma tabela acima) no dashboard ou via:
railway variables --set ENVIRONMENT=production --set ALLOW_TENANT_HEADER=true ...
```

## ⚠️ Antes de considerar "produção de verdade"

Este deploy é um **demo single-tenant**. Para produção:

- **Multi-tenancy**: `ALLOW_TENANT_HEADER=true` deixa o cliente informar o tenant
  pelo header — atalho de demo. Para multi-escola real, use **subdomínio por
  escola** (já suportado: `escola-a.<seu-domínio>`) com DNS wildcard e deixe
  `ALLOW_TENANT_HEADER=false`.
- **Seed**: o `CMD` roda `scripts.seed_dev`, que cria usuários demo com senhas
  conhecidas. Remova o `python -m scripts.seed_dev` do `CMD` (Dockerfile) quando
  houver dados reais, ou troque as senhas.
- **JWT_SECRET** forte e único; rotacione se vazar.
- Considere HTTPS (Railway já provê no domínio gerado) e backups do Postgres.
