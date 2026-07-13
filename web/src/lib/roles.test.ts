import { describe, expect, it } from "vitest";
import { ehProfessor, ehSecretaria, rotaInicial, temPapel } from "./roles";
import type { Usuario } from "../types";

function user(...papeis: string[]): Usuario {
  return { id: "u1", nome: "Fulano", email: "f@x.dev", ativo: true, papeis };
}

describe("roles", () => {
  it("temPapel casa qualquer um dos códigos", () => {
    expect(temPapel(user("professor"), "secretaria", "professor")).toBe(true);
    expect(temPapel(user("aluno"), "secretaria", "professor")).toBe(false);
    expect(temPapel(null, "secretaria")).toBe(false);
  });

  it("ehSecretaria abrange secretaria/admin_tenant/financeiro", () => {
    expect(ehSecretaria(user("secretaria"))).toBe(true);
    expect(ehSecretaria(user("admin_tenant"))).toBe(true);
    expect(ehSecretaria(user("financeiro"))).toBe(true);
    expect(ehSecretaria(user("responsavel"))).toBe(false);
  });

  it("ehProfessor", () => {
    expect(ehProfessor(user("professor"))).toBe(true);
    expect(ehProfessor(user("secretaria"))).toBe(false);
  });

  it("rotaInicial: secretaria > professor > responsável", () => {
    expect(rotaInicial(user("secretaria"))).toBe("/secretaria");
    expect(rotaInicial(user("admin_tenant"))).toBe("/secretaria");
    expect(rotaInicial(user("professor"))).toBe("/professor");
    expect(rotaInicial(user("responsavel"))).toBe("/portal");
    // secretaria vence quando há vários papéis
    expect(rotaInicial(user("professor", "secretaria"))).toBe("/secretaria");
  });
});
