# Deploy no Railway (single-service)

O deploy é **um único serviço**: o FastAPI serve a API (`/v1`) **e** o build do
front (SPA), na mesma URL. O tenant da escola é injetado no `index.html` em
runtime (`window.__ENV__`), então o front não precisa de rebuild por ambiente.

Já está tudo preparado no repositório:

- `Dockerfile` — multi-stage: builda o front (`web/`) e o embute no runtime do
  backend; o `CMD` chama `scripts/entrypoint.sh`.
- `scripts/entrypoint.sh` — `alembic upgrade head` → bootstrap/seed condicional
  → `uvicorn`.
- `railway.json` — builder DOCKERFILE + healthcheck em `/health`.
- `src/core/config.py` — normaliza a `DATABASE_URL` do Railway para psycopg3,
  expõe `ALLOW_TENANT_HEADER` / `DEMO_TENANT_ID` / `ALLOW_DEMO_SEED` e **recusa
  subir em produção com `JWT_SECRET` de placeholder**.

> Validado localmente e via `docker build`/`docker run` contra Postgres.

## Dois modos de deploy

| | Vitrine (demo) | Escola real |
|---|---|---|
| Usuários | criados pelo `seed_dev` (senhas conhecidas) | criados pelo `bootstrap_prod` |
| Variável-chave | `ALLOW_DEMO_SEED=true` | `BOOTSTRAP_*` (e **sem** `ALLOW_DEMO_SEED`) |
| Dado real | **nunca** | sim |

O seed demo **não roda por padrão**. Sem `ALLOW_DEMO_SEED=true` o entrypoint o
pula, e rodá-lo à mão em produção aborta com mensagem explicativa.

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
   | `ALLOW_TENANT_HEADER` | `true` (enquanto o deploy for single-tenant) |
   | `DEMO_TENANT_ID` | um UUID fixo (gere: `python -c "import uuid;print(uuid.uuid4())"`) |
   | `JWT_SECRET` | segredo forte: `python -c "import secrets;print(secrets.token_urlsafe(48))"` |

   Para **escola real**, acrescente:

   | Variável | Valor |
   |---|---|
   | `BOOTSTRAP_ESCOLA` | `Colégio Exemplo` |
   | `BOOTSTRAP_SUBDOMINIO` | `colegio-exemplo` |
   | `BOOTSTRAP_ADMIN_EMAIL` | e-mail do primeiro admin |
   | `BOOTSTRAP_ADMIN_SENHA` | senha forte (≥ 12 caracteres) |
   | `BOOTSTRAP_ADMIN_NOME` | opcional (default `Administrador`) |

   O tenant nasce com o UUID de `DEMO_TENANT_ID` — o mesmo que o front injeta,
   então o header casa sem rebuild. Se `BOOTSTRAP_ADMIN_SENHA` ficar vazia, uma
   senha forte é **gerada e impressa nos logs do deploy** (copie e apague o log).

   Para **vitrine**, acrescente `ALLOW_DEMO_SEED=true` (e, opcionalmente,
   `SEED_SENHA_ADMIN` / `SEED_SENHA_RESP` / `SEED_SENHA_SEC` / `SEED_SENHA_PROF`
   para não usar as senhas fracas do código).

   (O `PORT` é injetado pelo Railway automaticamente.)
5. **Deploy**. O container aplica migrations, cria o admin (uma vez) e sobe.
   Healthcheck em `/health`. Mudança de variável só vale depois de clicar
   **Deploy** (o Railway deixa a alteração *staged*).
6. **Gere o domínio**: *Settings → Networking → Generate Domain*.
7. Abra a URL e entre com o admin criado no passo 4.

## Caminho mais simples: manter como vitrine, com senhas fortes

Só a aba **Variables** — sem shell, sem CLI. Acrescente:

| Variável | Valor |
|---|---|
| `ALLOW_DEMO_SEED` | `true` |
| `SEED_SENHA_ADMIN` | senha forte |
| `SEED_SENHA_SEC` | senha forte |
| `SEED_SENHA_PROF` | senha forte |
| `SEED_SENHA_RESP` | senha forte |

Clique **Deploy**. No boot, o seed **atualiza a senha dos usuários demo que já
existem** (`admin@escola-a.dev` e companhia) para os valores das variáveis, e
revoga as sessões abertas. As senhas fracas do código (`admin12345` etc.) param
de funcionar.

> Quem não tiver `SEED_SENHA_*` correspondente fica com a senha intocada — o
> seed nunca reescreve uma senha com o default fraco.

Isso deixa a vitrine apresentável e sem credencial pública, mas **não é uma
escola real**: os dados continuam sendo os do cenário demo. Para dado real, siga
a seção abaixo.

## Migrar um deploy que já rodou o seed demo

Se a instância já tem `admin@escola-a.dev` e companhia (comportamento do
`CMD` antigo, que rodava o seed a cada boot):

```bash
# no shell do serviço (Railway → Deployments → ... → Shell), ou via railway run
python -m scripts.bootstrap_prod        # cria a escola e o admin reais
python -m scripts.desativar_demo        # dry-run: lista o que seria desativado
python -m scripts.desativar_demo --aplicar
```

`desativar_demo` marca `ativo=False` e revoga as sessões dos usuários
`@escola-a.dev` / `@escola-b.dev`. **Não apaga nada** — o histórico acadêmico e
financeiro que eles criaram continua íntegro e auditável.

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

## ⚠️ O que ainda falta para "produção de verdade"

- **Multi-tenancy**: `ALLOW_TENANT_HEADER=true` deixa o cliente informar o tenant
  pelo header — atalho de single-tenant. Para multi-escola real, use
  **subdomínio por escola** (já suportado: `escola-a.<seu-domínio>`) com DNS
  wildcard e `ALLOW_TENANT_HEADER=false`.
- **Rotação do `JWT_SECRET`** se houver suspeita de vazamento (invalida os
  tokens emitidos).
- **Backups do Postgres** (o Railway oferece snapshots do volume).
- **Troca de senha pelo próprio usuário** — hoje só o bootstrap define a senha
  inicial; não há fluxo de "esqueci minha senha".
