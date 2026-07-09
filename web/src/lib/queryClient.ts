import { QueryClient } from "@tanstack/react-query";
import { NaoAutenticado } from "./api";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: (falhas, erro) => {
        // Não insistir em 401 (sessão expirada) — o usuário vai para o login.
        if (erro instanceof NaoAutenticado) return false;
        return falhas < 2;
      },
    },
  },
});
