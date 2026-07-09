// Contexto de autenticação: login/logout e usuário atual (via /auth/me).

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { apiFetch } from "./api";
import { clearTokens, getAccessToken, getRefreshToken, setTokens } from "./tokens";
import type { TokenResposta, Usuario } from "../types";

interface AuthContextValue {
  user: Usuario | null;
  carregando: boolean;
  entrar: (email: string, senha: string) => Promise<void>;
  sair: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<Usuario | null>(null);
  const [carregando, setCarregando] = useState(true);

  // Ao montar: se há token, resolve o usuário; senão segue deslogado.
  useEffect(() => {
    let vivo = true;
    async function carregar() {
      if (!getAccessToken()) {
        setCarregando(false);
        return;
      }
      try {
        const me = await apiFetch<Usuario>("/auth/me");
        if (vivo) setUser(me);
      } catch {
        clearTokens();
        if (vivo) setUser(null);
      } finally {
        if (vivo) setCarregando(false);
      }
    }
    void carregar();
    return () => {
      vivo = false;
    };
  }, []);

  const entrar = useCallback(async (email: string, senha: string) => {
    const tokens = await apiFetch<TokenResposta>("/auth/login", {
      method: "POST",
      auth: false,
      body: { email, senha },
    });
    setTokens(tokens.access_token, tokens.refresh_token);
    const me = await apiFetch<Usuario>("/auth/me");
    setUser(me);
  }, []);

  const sair = useCallback(async () => {
    const refresh = getRefreshToken();
    try {
      if (refresh) {
        await apiFetch("/auth/logout", {
          method: "POST",
          auth: false,
          body: { refresh_token: refresh },
        });
      }
    } catch {
      // logout é best-effort; limpa localmente de qualquer forma.
    } finally {
      clearTokens();
      setUser(null);
    }
  }, []);

  const value = useMemo(
    () => ({ user, carregando, entrar, sair }),
    [user, carregando, entrar, sair],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth precisa estar dentro de <AuthProvider>.");
  return ctx;
}
