// Hooks de listagem/criação da estrutura acadêmica (Cadastros).

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "../../lib/api";
import type {
  AnoLetivo,
  Atribuicao,
  Curso,
  Disciplina,
  Serie,
  Turma,
} from "../../types";

function useLista<T>(key: string, path: string) {
  return useQuery({ queryKey: [key], queryFn: () => apiFetch<T[]>(path) });
}

function useCriar<TIn, TOut>(path: string, invalidar: string[]) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (dados: TIn) =>
      apiFetch<TOut>(path, { method: "POST", body: dados }),
    onSuccess: () =>
      invalidar.forEach((k) => qc.invalidateQueries({ queryKey: [k] })),
  });
}

// --- Ano letivo ---
export interface AnoLetivoInput {
  ano: number;
  descricao?: string;
}
export const useAnosLetivos = () =>
  useLista<AnoLetivo>("anos-letivos", "/academico/anos-letivos");
export const useCriarAnoLetivo = () =>
  useCriar<AnoLetivoInput, AnoLetivo>("/academico/anos-letivos", ["anos-letivos"]);

// --- Curso ---
export interface CursoInput {
  nome: string;
  codigo?: string;
}
export const useCursos = () => useLista<Curso>("cursos", "/academico/cursos");
export const useCriarCurso = () =>
  useCriar<CursoInput, Curso>("/academico/cursos", ["cursos"]);

// --- Série ---
export interface SerieInput {
  curso_id: string;
  nome: string;
  ordem?: number;
}
export const useSeries = () => useLista<Serie>("series", "/academico/series");
export const useCriarSerie = () =>
  useCriar<SerieInput, Serie>("/academico/series", ["series"]);

// --- Disciplina ---
export interface DisciplinaInput {
  nome: string;
  codigo?: string;
}
export const useDisciplinas = () =>
  useLista<Disciplina>("disciplinas", "/academico/disciplinas");
export const useCriarDisciplina = () =>
  useCriar<DisciplinaInput, Disciplina>("/academico/disciplinas", ["disciplinas"]);

// --- Turma ---
export interface TurmaInput {
  serie_id: string;
  ano_letivo_id: string;
  nome: string;
}
export const useCriarTurma = () =>
  useCriar<TurmaInput, Turma>("/academico/turmas", ["turmas"]);

// --- Atribuição (disciplina + professor por turma) ---
export interface AtribuicaoInput {
  disciplina_id: string;
  professor_id: string;
}
export function useAtribuicoes(turmaId: string | undefined) {
  return useQuery({
    queryKey: ["atribuicoes", turmaId],
    enabled: !!turmaId,
    queryFn: () =>
      apiFetch<Atribuicao[]>(`/academico/turmas/${turmaId}/disciplinas`),
  });
}
export function useCriarAtribuicao(turmaId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (dados: AtribuicaoInput) =>
      apiFetch<Atribuicao>(`/academico/turmas/${turmaId}/disciplinas`, {
        method: "POST",
        body: dados,
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["atribuicoes", turmaId] }),
  });
}
