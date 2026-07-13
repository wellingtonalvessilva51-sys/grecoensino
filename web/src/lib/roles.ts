import type { Usuario } from "../types";

export function temPapel(user: Usuario | null, ...codigos: string[]): boolean {
  if (!user) return false;
  return codigos.some((c) => user.papeis.includes(c));
}

export const ehSecretaria = (u: Usuario | null) =>
  temPapel(u, "secretaria", "admin_tenant", "financeiro");

export const ehProfessor = (u: Usuario | null) => temPapel(u, "professor");

/** Rota inicial conforme o papel do usuário (secretaria > professor > responsável). */
export function rotaInicial(user: Usuario | null): string {
  if (ehSecretaria(user)) return "/secretaria";
  if (ehProfessor(user)) return "/professor";
  return "/portal";
}
