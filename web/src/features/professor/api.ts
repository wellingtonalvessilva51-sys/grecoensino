// Hooks da área do Professor (atribuições e alunos das suas turmas).

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "../../lib/api";
import type { Matricula, ProfessorAtribuicao } from "../../types";

export function useMinhasAtribuicoes() {
  return useQuery({
    queryKey: ["minhas-atribuicoes"],
    queryFn: () =>
      apiFetch<ProfessorAtribuicao[]>("/academico/professor/atribuicoes"),
  });
}

export function useMatriculasDaTurma(turmaId: string | undefined) {
  return useQuery({
    queryKey: ["turma-matriculas", turmaId],
    enabled: !!turmaId,
    queryFn: () =>
      apiFetch<Matricula[]>(`/academico/turmas/${turmaId}/matriculas`),
  });
}
