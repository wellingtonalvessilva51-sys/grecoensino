// Hooks para lançamento de Notas e Frequência.

import {
  useMutation,
  useQueries,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { apiFetch } from "../../lib/api";
import type { ConfigAcademica, Frequencia, Nota } from "../../types";

export function useConfig() {
  return useQuery({
    queryKey: ["config"],
    queryFn: () => apiFetch<ConfigAcademica>("/academico/config"),
  });
}

/** Notas de cada matrícula (uma query por aluno) para pré-preencher os campos. */
export function useNotasPorMatricula(matriculaIds: string[]) {
  const results = useQueries({
    queries: matriculaIds.map((id) => ({
      queryKey: ["notas", id],
      queryFn: () => apiFetch<Nota[]>(`/academico/matriculas/${id}/notas`),
    })),
  });
  const mapa = new Map<string, Nota[]>();
  results.forEach((r, i) => mapa.set(matriculaIds[i], r.data ?? []));
  return { mapa, carregando: results.some((r) => r.isLoading) };
}

export function useLancarNota() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (dados: {
      matricula_id: string;
      disciplina_id: string;
      periodo: number;
      valor: number;
    }) => apiFetch<Nota>("/academico/notas", { method: "POST", body: dados }),
    onSuccess: (_d, vars) =>
      qc.invalidateQueries({ queryKey: ["notas", vars.matricula_id] }),
  });
}

export function useLancarFrequencia() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (dados: {
      matricula_id: string;
      data: string;
      presente: boolean;
      justificada: boolean;
    }) =>
      apiFetch<Frequencia>("/academico/frequencias", {
        method: "POST",
        body: dados,
      }),
    onSuccess: (_d, vars) =>
      qc.invalidateQueries({ queryKey: ["frequencias", vars.matricula_id] }),
  });
}
