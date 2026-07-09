import { Navigate } from "react-router-dom";
import type { ReactNode } from "react";
import { useAuth } from "../lib/auth";

/** Só renderiza os filhos se houver usuário logado; senão manda para /login. */
export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { user, carregando } = useAuth();
  if (carregando) return <div className="tela-centro">Carregando…</div>;
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}
