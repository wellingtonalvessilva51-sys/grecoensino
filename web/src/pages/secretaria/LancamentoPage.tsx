import { useEffect, useMemo, useState, type FormEvent } from "react";
import { ApiError } from "../../lib/api";
import { useMatriculas, useTurmas } from "../../features/secretaria/api";
import { useAtribuicoes, useDisciplinas } from "../../features/secretaria/cadastros";
import {
  useConfig,
  useLancarFrequencia,
  useLancarNota,
  useNotasPorMatricula,
} from "../../features/secretaria/lancamento";
import type { Matricula } from "../../types";

type Aba = "notas" | "frequencia";

export function LancamentoPage() {
  const turmas = useTurmas();
  const matriculas = useMatriculas();
  const [turmaId, setTurmaId] = useState("");
  const [aba, setAba] = useState<Aba>("frequencia");

  const alunos = useMemo(
    () => (matriculas.data ?? []).filter((m) => m.turma_id === turmaId),
    [matriculas.data, turmaId],
  );

  return (
    <div className="cartao">
      <div className="cartao-cab">
        <h2>Lançamento</h2>
        <select value={turmaId} onChange={(e) => setTurmaId(e.target.value)}>
          <option value="">Selecione a turma…</option>
          {turmas.data?.map((t) => (
            <option key={t.id} value={t.id}>
              {t.serie_nome} · {t.nome} · {t.ano}
            </option>
          ))}
        </select>
      </div>

      {!turmaId && <p className="sub">Escolha uma turma para lançar.</p>}

      {turmaId && (
        <>
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

          {alunos.length === 0 ? (
            <p className="sub">Nenhum aluno matriculado nesta turma.</p>
          ) : aba === "frequencia" ? (
            <FrequenciaTab alunos={alunos} />
          ) : (
            <NotasTab turmaId={turmaId} alunos={alunos} />
          )}
        </>
      )}
    </div>
  );
}

function FrequenciaTab({ alunos }: { alunos: Matricula[] }) {
  const lancar = useLancarFrequencia();
  const [data, setData] = useState("");
  const [presentes, setPresentes] = useState<Record<string, boolean>>({});
  const [msg, setMsg] = useState<string | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  function presente(id: string): boolean {
    return presentes[id] ?? true; // default: presente
  }

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

function NotasTab({ turmaId, alunos }: { turmaId: string; alunos: Matricula[] }) {
  const config = useConfig();
  const atribuicoes = useAtribuicoes(turmaId);
  const disciplinas = useDisciplinas();
  const lancar = useLancarNota();
  const alunoIds = useMemo(() => alunos.map((m) => m.id), [alunos]);
  const { mapa: notasPorAluno } = useNotasPorMatricula(alunoIds);

  const [disciplinaId, setDisciplinaId] = useState("");
  const [periodo, setPeriodo] = useState(1);
  const [valores, setValores] = useState<Record<string, string>>({});
  const [msg, setMsg] = useState<string | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  // Disciplinas atribuídas a esta turma (nome via mapa).
  const nomeDisc = useMemo(() => {
    const m = new Map<string, string>();
    disciplinas.data?.forEach((d) => m.set(d.id, d.nome));
    return m;
  }, [disciplinas.data]);
  const discDaTurma = atribuicoes.data ?? [];

  // Pré-preenche os campos com as notas já lançadas para disciplina+período.
  useEffect(() => {
    if (!disciplinaId) return;
    const iniciais: Record<string, string> = {};
    alunos.forEach((m) => {
      const nota = (notasPorAluno.get(m.id) ?? []).find(
        (n) => n.disciplina_id === disciplinaId && n.periodo === periodo,
      );
      iniciais[m.id] = nota ? nota.valor : "";
    });
    setValores(iniciais);
    // notasPorAluno é recriado a cada render; dependemos de disciplina/período/alunos.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [disciplinaId, periodo, alunos]);

  const numPeriodos = config.data?.num_periodos ?? 4;

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
      <div className="linha">
        <label>
          Disciplina
          <select
            value={disciplinaId}
            onChange={(e) => setDisciplinaId(e.target.value)}
            required
          >
            <option value="" disabled>
              Selecione…
            </option>
            {discDaTurma.map((a) => (
              <option key={a.id} value={a.disciplina_id}>
                {nomeDisc.get(a.disciplina_id) ?? "—"}
              </option>
            ))}
          </select>
        </label>
        <label>
          Período
          <select value={periodo} onChange={(e) => setPeriodo(Number(e.target.value))}>
            {Array.from({ length: numPeriodos }, (_, i) => i + 1).map((p) => (
              <option key={p} value={p}>
                {p}º
              </option>
            ))}
          </select>
        </label>
      </div>

      {discDaTurma.length === 0 && (
        <p className="sub">
          Esta turma não tem disciplinas atribuídas. Cadastre em Cadastros →
          Disciplinas por turma.
        </p>
      )}

      {disciplinaId && (
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
      )}

      {erro && <p className="erro">{erro}</p>}
      {msg && <p className="ok">{msg}</p>}
      {disciplinaId && (
        <button type="submit" disabled={lancar.isPending}>
          {lancar.isPending ? "Salvando…" : "Salvar notas"}
        </button>
      )}
    </form>
  );
}
