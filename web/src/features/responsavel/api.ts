// Hooks de dados do Portal do Responsável (TanStack Query sobre a API /v1).

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "../../lib/api";
import type {
  Boletim,
  FrequenciaResumo,
  Matricula,
  RecadoInboxItem,
  Titulo,
} from "../../types";

export function useMatriculas() {
  return useQuery({
    queryKey: ["matriculas"],
    queryFn: () => apiFetch<Matricula[]>("/academico/matriculas"),
  });
}

export function useBoletim(matriculaId: string | undefined) {
  return useQuery({
    queryKey: ["boletim", matriculaId],
    enabled: !!matriculaId,
    queryFn: () =>
      apiFetch<Boletim>(`/academico/matriculas/${matriculaId}/boletim`),
  });
}

export function useFrequenciaResumo(matriculaId: string | undefined) {
  return useQuery({
    queryKey: ["frequencia-resumo", matriculaId],
    enabled: !!matriculaId,
    queryFn: () =>
      apiFetch<FrequenciaResumo>(
        `/academico/matriculas/${matriculaId}/frequencia-resumo`,
      ),
  });
}

export function useTitulos() {
  return useQuery({
    queryKey: ["titulos"],
    queryFn: () => apiFetch<Titulo[]>("/financeiro/titulos"),
  });
}

export function useRecados() {
  return useQuery({
    queryKey: ["recados"],
    queryFn: () => apiFetch<RecadoInboxItem[]>("/comunicacao/recados"),
  });
}

export function useMarcarRecadoLido() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (destinatarioId: string) =>
      apiFetch<RecadoInboxItem>(
        `/comunicacao/recados/destinatarios/${destinatarioId}/lido`,
        { method: "POST" },
      ),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["recados"] }),
  });
}
