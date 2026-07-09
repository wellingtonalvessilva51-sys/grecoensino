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
  turma_id: string;
  situacao: string;
  data_matricula: string;
}

export interface BoletimDisciplina {
  disciplina_id: string;
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

export interface Titulo {
  id: string;
  aluno_id: string;
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
