/// <reference types="vitest/config" />
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";

// PWA fora do ambiente de teste (evita SW/virtual modules durante o Vitest).
const pwa = process.env.VITEST
  ? []
  : [
      VitePWA({
        registerType: "autoUpdate",
        injectRegister: "auto",
        includeAssets: ["icon.svg"],
        manifest: {
          name: "Gestão Educacional",
          short_name: "Gestão Edu",
          description: "Portal da Gestão Educacional (responsável, professor, secretaria).",
          lang: "pt-BR",
          theme_color: "#1f6feb",
          background_color: "#ffffff",
          display: "standalone",
          start_url: "/",
          icons: [
            {
              src: "icon.svg",
              sizes: "any",
              type: "image/svg+xml",
              purpose: "any maskable",
            },
          ],
        },
        workbox: {
          globPatterns: ["**/*.{js,css,html,svg}"],
        },
      }),
    ];

// Dev server em http://localhost:5173. O backend (FastAPI) libera essa origem
// via CORS (ver src/main.py). As chamadas vão direto para VITE_API_BASE_URL.
export default defineConfig({
  plugins: [react(), ...pwa],
  server: {
    port: 5173,
    strictPort: true,
  },
  test: {
    environment: "jsdom",
    setupFiles: "./src/test/setup.ts",
    css: false,
    env: {
      VITE_TENANT_ID: "tenant-123",
      VITE_API_BASE_URL: "http://api.test",
    },
  },
});
