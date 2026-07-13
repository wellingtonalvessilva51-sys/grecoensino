import { useEffect, useMemo, useState, type FormEvent } from "react";
import { useAuth } from "../../lib/auth";
import { ApiError } from "../../lib/api";
import {
  useMatriculasDaTurma,
  useMinhasAtribuicoes,
} from "../../features/professor/api";
import {
  useConfig,
  useLancarFrequencia,
  useLancarNota,
  useNotasPorMatricula,
} from "../../features/secretaria/lancamento";
import type { Matricula, ProfessorAtribuicao } from "../../types";

type Aba = "frequencia" | "notas";

export function ProfessorPage() {
  const { user, sair } = useAuth();
  const atribs = useMinhasAtribuicoes();
  const [sel, setSel] = useState(0);
  const lista = atribs.data ?? [];
  const atual = lista[sel];

  return (
    <div className="pagina">
      <header className="topo">
        <div>
          <strong>Gestão Educacional</strong>
          <span className="sub"> · Professor</span>
        </div>
        <div className="topo-dir">
          <span>{user?.nome}</span>
          <button className="link" onClick={() => void sair()}>
            Sair
          </button>
        </div>
      </header>

      <main className="conteudo">
        {atribs.isLoading && <p>Carregando suas turmas…</p>}
        {atribs.isError && <p className="erro">Falha ao carregar suas turmas.</p>}
        {!atribs.isLoading && lista.length === 0 && (
          <p>Você não leciona nenhuma disciplina atribuída.</p>
        )}

        {lista.length > 0 && atual && (
          <>
            <label className="seletor">
              Turma / disciplina
              <select value={sel} onChange={(e) => setSel(Number(e.target.value))}>
                {lista.map((a, i) => (
                  <option key={`${a.turma_id}-${a.disciplina_id}`} value={i}>
                    {a.serie_nome} · {a.turma_nome} · {a.ano} — {a.disciplina_nome}
                  </option>
                ))}
              </select>
            </label>
            <Lancamento atribuicao={atual} />
          </>
        )}
      </main>
    </div>
  );
}

function Lancamento({ atribuicao }: { atribuicao: ProfessorAtribuicao }) {
  const [aba, setAba] = useState<Aba>("frequencia");
  const matriculas = useMatriculasDaTurma(atribuicao.turma_id);
  const alunos = matriculas.data ?? [];

  return (
    <div className="cartao">
      <div className="abas">
        <button
          className={aba === "frequencia" ? "aba ativa" : "aba"}
          onClick={() => setAba("frequencia")}
        >
          Frequência
        </button>
        <button
          className={aba === "notas" ? "aba ativa" : "aba"}
          onClick={() => setAba("notas")}
        >
          Notas
        </button>
      </div>

      {matriculas.isLoading && <p>Carregando alunos…</p>}
      {matriculas.isError && <p className="erro">Falha ao carregar alunos.</p>}
      {!matriculas.isLoading && alunos.length === 0 && (
        <p className="sub">Nenhum aluno matriculado nesta turma.</p>
      )}

      {alunos.length > 0 &&
        (aba === "frequencia" ? (
          <FrequenciaTab alunos={alunos} />
        ) : (
          <NotasTab alunos={alunos} disciplinaId={atribuicao.disciplina_id} />
        ))}
    </div>
  );
}

function FrequenciaTab({ alunos }: { alunos: Matricula[] }) {
  const lancar = useLancarFrequencia();
  const [data, setData] = useState("");
  const [presentes, setPresentes] = useState<Record<string, boolean>>({});
  const [msg, setMsg] = useState<string | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const presente = (id: string) => presentes[id] ?? true;

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setMsg(null);
    setErro(null);
    try {
      const r = await Promise.allSettled(
        alunos.map((m) =>
          lancar.mutateAsync({
            matricula_id: m.id,
            data,
            presente: presente(m.id),
            justificada: false,
          }),
        ),
      );
      const oks = r.filter((x) => x.status === "fulfilled").length;
      setMsg(`Frequência salva para ${oks}/${alunos.length} alunos.`);
    } catch (err) {
      setErro(err instanceof ApiError ? err.message : "Falha ao salvar.");
    }
  }

  return (
    <form className="form" onSubmit={onSubmit}>
      <label className="seletor">
        Data (dia letivo)
        <input type="date" value={data} onChange={(e) => setData(e.target.value)} required />
      </label>
      <table>
        <thead>
          <tr>
            <th>Aluno</th>
            <th>Presente</th>
          </tr>
        </thead>
        <tbody>
          {alunos.map((m) => (
            <tr key={m.id}>
              <td>{m.aluno_nome}</td>
              <td>
                <input
                  type="checkbox"
                  checked={presente(m.id)}
                  onChange={(e) =>
                    setPresentes((p) => ({ ...p, [m.id]: e.target.checked }))
                  }
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {erro && <p className="erro">{erro}</p>}
      {msg && <p className="ok">{msg}</p>}
      <button type="submit" disabled={lancar.isPending || !data}>
        {lancar.isPending ? "Salvando…" : "Salvar frequência"}
      </button>
    </form>
  );
}

function NotasTab({
  alunos,
  disciplinaId,
}: {
  alunos: Matricula[];
  disciplinaId: string;
}) {
  const config = useConfig();
  const lancar = useLancarNota();
  const alunoIds = useMemo(() => alunos.map((m) => m.id), [alunos]);
  const { mapa: notasPorAluno } = useNotasPorMatricula(alunoIds);
  const [periodo, setPeriodo] = useState(1);
  const [valores, setValores] = useState<Record<string, string>>({});
  const [msg, setMsg] = useState<string | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const numPeriodos = config.data?.num_periodos ?? 4;

  useEffect(() => {
    const iniciais: Record<string, string> = {};
    alunos.forEach((m) => {
      const nota = (notasPorAluno.get(m.id) ?? []).find(
        (n) => n.disciplina_id === disciplinaId && n.periodo === periodo,
      );
      iniciais[m.id] = nota ? nota.valor : "";
    });
    setValores(iniciais);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [periodo, disciplinaId, alunos]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setMsg(null);
    setErro(null);
    try {
      const aSalvar = alunos.filter((m) => valores[m.id] !== "" && valores[m.id] != null);
      const r = await Promise.allSettled(
        aSalvar.map((m) =>
          lancar.mutateAsync({
            matricula_id: m.id,
            disciplina_id: disciplinaId,
            periodo,
            valor: Number(valores[m.id]),
          }),
        ),
      );
      const oks = r.filter((x) => x.status === "fulfilled").length;
      setMsg(`Notas salvas: ${oks}/${aSalvar.length}.`);
    } catch (err) {
      setErro(err instanceof ApiError ? err.message : "Falha ao salvar.");
    }
  }

  return (
    <form className="form" onSubmit={onSubmit}>
      <label className="seletor">
        Período
        <select value={periodo} onChange={(e) => setPeriodo(Number(e.target.value))}>
          {Array.from({ length: numPeriodos }, (_, i) => i + 1).map((p) => (
            <option key={p} value={p}>
              {p}º
            </option>
          ))}
        </select>
      </label>
      <table>
        <thead>
          <tr>
            <th>Aluno</th>
            <th>Nota (0–10)</th>
          </tr>
        </thead>
        <tbody>
          {alunos.map((m) => (
            <tr key={m.id}>
              <td>{m.aluno_nome}</td>
              <td>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  max="10"
                  value={valores[m.id] ?? ""}
                  onChange={(e) =>
                    setValores((v) => ({ ...v, [m.id]: e.target.value }))
                  }
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {erro && <p className="erro">{erro}</p>}
      {msg && <p className="ok">{msg}</p>}
      <button type="submit" disabled={lancar.isPending}>
        {lancar.isPending ? "Salvando…" : "Salvar notas"}
      </button>
    </form>
  );
}
