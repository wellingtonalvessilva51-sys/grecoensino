// Tipos espelhando os contratos da API (/v1). Ver Swagger em /docs.

export interface TokenResposta {
  access_token: string;
  refresh_token: string;
  expira_em_min: number;
}

export interface Usuario {
  id: string;
  nome: string;
  email: string;
  ativo: boolean;
  papeis: string[];
}

export interface Matricula {
  id: string;
  aluno_id: string;
  aluno_nome: string;
  turma_id: string;
  situacao: string;
  data_matricula: string;
}

export interface AnoLetivo {
  id: string;
  ano: number;
  descricao: string | null;
  situacao: string;
}

export interface Curso {
  id: string;
  nome: string;
  codigo: string | null;
}

export interface Serie {
  id: string;
  curso_id: string;
  nome: string;
  ordem: number | null;
}

export interface Disciplina {
  id: string;
  nome: string;
  codigo: string | null;
}

export interface Turma {
  id: string;
  serie_id: string;
  serie_nome: string;
  ano_letivo_id: string;
  ano: number;
  nome: string;
}

export interface Atribuicao {
  id: string;
  turma_id: string;
  disciplina_id: string;
  professor_id: string;
}

export interface Nota {
  id: string;
  matricula_id: string;
  disciplina_id: string;
  periodo: number;
  valor: string;
}

export interface Frequencia {
  id: string;
  matricula_id: string;
  data: string;
  presente: boolean;
  justificada: boolean;
}

export interface ConfigAcademica {
  id: string;
  media_minima: string;
  num_periodos: number;
  pesos_periodos: string[];
  frequencia_minima_percentual: string;
}

export interface BoletimDisciplina {
  disciplina_id: string;
  disciplina_nome: string;
  media: string;
  periodos_lancados: number;
  completa: boolean;
  situacao: "cursando" | "aprovado" | "reprovado_nota";
}

export interface FrequenciaResumo {
  matricula_id: string;
  dias_letivos: number;
  presencas: number;
  faltas: number;
  faltas_justificadas: number;
  percentual: string;
  frequencia_minima: string;
  suficiente: boolean;
}

export interface Boletim {
  matricula_id: string;
  aluno_nome: string;
  media_minima: string;
  num_periodos: number;
  disciplinas: BoletimDisciplina[];
  frequencia: FrequenciaResumo;
  situacao_final:
    | "cursando"
    | "aprovado"
    | "reprovado_nota"
    | "reprovado_frequencia";
}

export interface TituloItem {
  id: string;
  descricao: string;
  valor: string;
}

export interface Pessoa {
  id: string;
  nome: string;
  cpf: string | null;
  data_nascimento: string | null;
  usuario_id: string | null;
}

export interface Pagamento {
  id: string;
  titulo_id: string;
  valor: string;
  data_pagamento: string;
}

export interface Titulo {
  id: string;
  aluno_id: string;
  aluno_nome: string;
  competencia: string;
  vencimento: string;
  descricao: string | null;
  valor_total: string;
  status: "pendente" | "parcial" | "liquidado";
  total_pago: string;
  saldo: string;
  itens: TituloItem[];
}

export interface RecadoInboxItem {
  destinatario_id: string;
  recado_id: string;
  titulo: string;
  mensagem: string;
  created_at: string;
  pessoa_id: string;
  lido_em: string | null;
}
