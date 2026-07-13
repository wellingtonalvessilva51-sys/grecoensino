// Configuração: runtime (window.__ENV__, injetado pelo backend no deploy) tem
// precedência sobre as env vars de build do Vite (usadas em dev).

const injetado =
  typeof window !== "undefined" ? window.__ENV__ : undefined;

export const API_BASE_URL = (
  injetado?.apiBaseUrl ??
  import.meta.env.VITE_API_BASE_URL ??
  "http://localhost:8000"
).replace(/\/+$/, ""); // sem barra final

// Em dev, o tenant é enviado no header X-Tenant-ID. No deploy demo, vem do
// window.__ENV__. Em produção multi-tenant real, fica vazio (resolve por host).
export const DEV_TENANT_ID =
  injetado?.tenantId ?? import.meta.env.VITE_TENANT_ID ?? "";
