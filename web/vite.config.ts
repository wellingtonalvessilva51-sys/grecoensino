import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev server em http://localhost:5173. O backend (FastAPI) libera essa origem
// via CORS (ver src/main.py). As chamadas vão direto para VITE_API_BASE_URL.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
  },
});
