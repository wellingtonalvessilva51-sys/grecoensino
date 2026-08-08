import { describe, expect, it } from "vitest";
import { manifestConfig, workboxConfig } from "../pwa.config";

// Regressão de um bug real em produção: com `index.html` no precache, o service
// worker passou a responder as navegações com o HTML do build — sem a injeção
// de `window.__ENV__` feita pelo backend. O front ficava sem tenant e o login
// respondia 500 `tenant_ausente` para quem já tivesse visitado o site.
describe("config do PWA", () => {
  it("nao precacheia HTML", () => {
    for (const padrao of workboxConfig.globPatterns) {
      expect(padrao).not.toContain("html");
    }
  });

  it("nao registra NavigationRoute (navegacao vai a rede)", () => {
    expect(workboxConfig.navigateFallback).toBeUndefined();
  });

  it("ainda precacheia os assets do app", () => {
    const juntos = workboxConfig.globPatterns.join(" ");
    expect(juntos).toContain("js");
    expect(juntos).toContain("css");
  });

  it("segue instalavel (manifest standalone com icone)", () => {
    expect(manifestConfig.display).toBe("standalone");
    expect(manifestConfig.icons.length).toBeGreaterThan(0);
  });
});
