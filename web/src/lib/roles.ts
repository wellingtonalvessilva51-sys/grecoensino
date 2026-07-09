import type { Usuario } from "../types";

export function temPapel(user: Usuario | null, ...codigos: string[]): boolean {
  if (!user) return false;
  return codigos.some((c) => user.papeis.includes(c));
}

export const ehSecretaria = (u: Usuario | null) =>
  temPapel(u, "secretaria", "admin_tenant", "financeiro");

/** Rota inicial conforme o papel do usuário. */
export function rotaInicial(user: Usuario | null): string {
  if (ehSecretaria(user)) return "/secretaria";
  return "/portal";
}
