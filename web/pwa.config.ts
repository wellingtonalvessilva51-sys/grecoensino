// Config do PWA isolada aqui para poder ser testada (ver src/pwa.config.test.ts).
//
// Regra que não pode se perder: `index.html` NUNCA entra no precache. O backend
// injeta a config de runtime (`window.__ENV__` com o tenant) no HTML ao servir;
// um index.html precacheado é a versão do build, sem essa injeção — o front fica
// sem tenant e o login passa a responder 500 `tenant_ausente`.

export const workboxConfig = {
  globPatterns: ["**/*.{js,css,svg}"],
  // Sem NavigationRoute: navegação sempre vai à rede, então o HTML servido é
  // sempre o injetado. Os assets seguem precacheados (carga rápida).
  navigateFallback: undefined,
};

export const manifestConfig = {
  name: "Gestão Educacional",
  short_name: "Gestão Edu",
  description: "Portal da Gestão Educacional (responsável, professor, secretaria).",
  lang: "pt-BR",
  theme_color: "#1f6feb",
  background_color: "#ffffff",
  display: "standalone" as const,
  start_url: "/",
  icons: [
    {
      src: "icon.svg",
      sizes: "any",
      type: "image/svg+xml",
      purpose: "any maskable",
    },
  ],
};
