/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_TENANT_ID?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

// Config de runtime injetada pelo backend (deploy single-service).
interface Window {
  __ENV__?: {
    tenantId?: string;
    apiBaseUrl?: string;
  };
}
