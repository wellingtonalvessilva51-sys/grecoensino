// Hooks de dados da área da Secretaria (Financeiro).

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "../../lib/api";
import type { Pagamento, Pessoa, Titulo } from "../../types";

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
