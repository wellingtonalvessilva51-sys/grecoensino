/// <reference types="vitest/config" />
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// Dev server em http://localhost:5173. O backend (FastAPI) libera essa origem
// via CORS (ver src/main.py). As chamadas vão direto para VITE_API_BASE_URL.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
  },
  test: {
    environment: "jsdom",
    setupFiles: "./src/test/setup.ts",
    css: false,
    // Env de teste: tenant fixo e base da API previsível.
    env: {
      VITE_TENANT_ID: "tenant-123",
      VITE_API_BASE_URL: "http://api.test",
    },
  },
});
