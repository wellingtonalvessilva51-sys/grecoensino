# Front web — Portal (Gestão Educacional)

Cliente React (Vite + TypeScript) que consome a API `/v1`. Primeira fatia:
**login (JWT + refresh automático) → Portal do Responsável** (boletim,
frequência, títulos e recados do dependente).

## Pré-requisitos

- Node.js LTS (18+). Verifique com `node --version`.
- API rodando (por padrão em `http://localhost:8000`):
  ```
  # na raiz do repo
  .\venv\Scripts\python.exe -m uvicorn src.main:app --reload
  ```

## Rodar

```bash
cd web
npm install
copy .env.example .env      # e preencher VITE_TENANT_ID (UUID da escola em dev)
npm run dev                 # http://localhost:5173
```

O backend libera a origem `http://localhost:5173` via CORS (`src/main.py`,
config `CORS_ORIGINS`).

### VITE_TENANT_ID (multi-tenancy em dev)

Em desenvolvimento o tenant vai no header `X-Tenant-ID`. Pegue o UUID da escola:

```bash
# na raiz do repo, com o Postgres no ar
.\venv\Scripts\python.exe -m scripts.seed_dev   # cria/mostra tenants demo
```

Em produção o tenant é resolvido pelo subdomínio (`escola-a.<dominio>`), então
`VITE_TENANT_ID` fica vazio.

## Estrutura

```
src/
  lib/          api (fetch + refresh), auth (contexto), tokens, config, queryClient
  routes/       ProtectedRoute (guarda de rota)
  features/     responsavel/ (hooks de dados: boletim, frequência, títulos, recados)
  pages/        LoginPage, PortalResponsavel
  types.ts      contratos espelhando a API
```

## Scripts

- `npm run dev` — servidor de desenvolvimento (HMR).
- `npm run build` — typecheck + build de produção.
- `npm run typecheck` — só checagem de tipos.
- `npm run test` — testes (Vitest + Testing Library). `npm run test:watch` para watch.
