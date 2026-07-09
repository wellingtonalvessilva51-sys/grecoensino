// Hooks de dados da área da Secretaria (Financeiro).

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "../../lib/api";
import type { Matricula, Pagamento, Pessoa, Titulo, Turma } from "../../types";

export interface ItemInput {
  descricao: string;
  valor: number;
}

export interface TituloInput {
  aluno_id: string;
  competencia: string;
  vencimento: string;
  descricao?: string;
  itens: ItemInput[];
}

export function usePessoas() {
  return useQuery({
    queryKey: ["pessoas"],
    queryFn: () => apiFetch<Pessoa[]>("/pessoas"),
  });
}

export interface PessoaInput {
  nome: string;
  cpf?: string;
  data_nascimento?: string;
}

export function useCriarPessoa() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (dados: PessoaInput) =>
      apiFetch<Pessoa>("/pessoas", { method: "POST", body: dados }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["pessoas"] }),
  });
}

export function useTurmas() {
  return useQuery({
    queryKey: ["turmas"],
    queryFn: () => apiFetch<Turma[]>("/academico/turmas"),
  });
}

export function useMatriculas() {
  return useQuery({
    queryKey: ["matriculas-sec"],
    queryFn: () => apiFetch<Matricula[]>("/academico/matriculas"),
  });
}

export interface MatriculaInput {
  aluno_id: string;
  turma_id: string;
  cobranca_inicial?: { valor: number; competencia: string; vencimento: string };
}

export function useCriarMatricula() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (dados: MatriculaInput) =>
      apiFetch<Matricula>("/academico/matriculas", { method: "POST", body: dados }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["matriculas-sec"] });
      qc.invalidateQueries({ queryKey: ["titulos-sec"] }); // cobrança pode gerar título
    },
  });
}

export function useTitulos(status: string) {
  const qs = status ? `?status=${status}` : "";
  return useQuery({
    queryKey: ["titulos-sec", status],
    queryFn: () => apiFetch<Titulo[]>(`/financeiro/titulos${qs}`),
  });
}

export function usePagamentos(tituloId: string | undefined) {
  return useQuery({
    queryKey: ["pagamentos", tituloId],
    enabled: !!tituloId,
    queryFn: () => apiFetch<Pagamento[]>(`/financeiro/titulos/${tituloId}/pagamentos`),
  });
}

export function useCriarTitulo() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (dados: TituloInput) =>
      apiFetch<Titulo>("/financeiro/titulos", { method: "POST", body: dados }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["titulos-sec"] }),
  });
}

export function useRegistrarPagamento(tituloId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (dados: { valor: number; data_pagamento?: string }) =>
      apiFetch<Pagamento>(`/financeiro/titulos/${tituloId}/pagamentos`, {
        method: "POST",
        body: dados,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["titulos-sec"] });
      qc.invalidateQueries({ queryKey: ["pagamentos", tituloId] });
    },
  });
}
