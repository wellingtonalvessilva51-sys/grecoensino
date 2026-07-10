// Hooks de Recados (envio + enviados) para a Secretaria.

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "../../lib/api";
import type { RecadoEnviado } from "../../types";

export function useEnviados() {
  return useQuery({
    queryKey: ["recados-enviados"],
    queryFn: () => apiFetch<RecadoEnviado[]>("/comunicacao/recados/enviados"),
  });
}

export interface RecadoInput {
  titulo: string;
  mensagem: string;
  destinatarios: string[]; // pessoa_id
}

export function useCriarRecado() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (dados: RecadoInput) =>
      apiFetch<RecadoEnviado>("/comunicacao/recados", { method: "POST", body: dados }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["recados-enviados"] }),
  });
}
