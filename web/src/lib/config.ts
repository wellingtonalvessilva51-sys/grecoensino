// Configuração lida das env vars do Vite (build-time).

export const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000"
).replace(/\/+$/, ""); // sem barra final

// Em dev, o tenant é enviado no header X-Tenant-ID. Em produção fica vazio e o
// backend resolve pelo subdomínio.
export const DEV_TENANT_ID = import.meta.env.VITE_TENANT_ID ?? "";
