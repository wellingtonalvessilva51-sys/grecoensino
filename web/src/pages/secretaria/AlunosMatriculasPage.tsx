import { useMemo, useState, type FormEvent } from "react";
import { ApiError } from "../../lib/api";
import { money } from "../../lib/format";
import {
  useCriarMatricula,
  useCriarPessoa,
  useMatriculas,
  usePessoas,
  useTurmas,
} from "../../features/secretaria/api";
import type { Turma } from "../../types";

export function AlunosMatriculasPage() {
  return (
    <div className="fin-grade">
      <div className="fin-lado">
        <ListaAlunos />
        <NovoAluno />
      </div>
      <div className="fin-lado">
        <ListaMatriculas />
        <NovaMatricula />
      </div>
    </div>
  );
}

function ListaAlunos() {
  const pessoas = usePessoas();
  return (
    <section className="cartao">
      <h2>Pessoas</h2>
      {pessoas.isLoading && <p>Carregando…</p>}
      {pessoas.isError && <p className="erro">Falha ao carregar pessoas.</p>}
      {pessoas.data && (
        <table>
          <thead>
            <tr>
              <th>Nome</th>
              <th>CPF</th>
              <th>Nascimento</th>
            </tr>
          </thead>
          <tbody>
            {pessoas.data.map((p) => (
              <tr key={p.id}>
                <td>{p.nome}</td>
                <td>{p.cpf ?? "—"}</td>
                <td>{p.data_nascimento ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}

function NovoAluno() {
  const criar = useCriarPessoa();
  const [nome, setNome] = useState("");
  const [cpf, setCpf] = useState("");
  const [nascimento, setNascimento] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [ok, setOk] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setErro(null);
    setOk(false);
    try {
      await criar.mutateAsync({
        nome,
        cpf: cpf || undefined,
        data_nascimento: nascimento || undefined,
      });
      setOk(true);
      setNome("");
      setCpf("");
      setNascimento("");
    } catch (err) {
      setErro(err instanceof ApiError ? err.message : "Falha ao criar pessoa.");
    }
  }

  return (
    <section className="cartao">
      <h2>Nova pessoa</h2>
      <form className="form" onSubmit={onSubmit}>
        <label>
          Nome
          <input value={nome} onChange={(e) => setNome(e.target.value)} required />
        </label>
        <div className="linha">
          <label>
            CPF (opcional)
            <input
              value={cpf}
              onChange={(e) => setCpf(e.target.value)}
              placeholder="11 dígitos"
            />
          </label>
          <label>
            Nascimento (opcional)
            <input
              type="date"
              value={nascimento}
              onChange={(e) => setNascimento(e.target.value)}
            />
          </label>
        </div>
        {erro && <p className="erro">{erro}</p>}
        {ok && <p className="ok">Pessoa cadastrada.</p>}
        <button type="submit" disabled={criar.isPending}>
          {criar.isPending ? "Salvando…" : "Cadastrar"}
        </button>
      </form>
    </section>
  );
}

function turmaLabel(t: Turma): string {
  return `${t.serie_nome} · ${t.nome} · ${t.ano}`;
}

function ListaMatriculas() {
  const matriculas = useMatriculas();
  const turmas = useTurmas();
  const mapaTurma = useMemo(() => {
    const m = new Map<string, string>();
    turmas.data?.forEach((t) => m.set(t.id, turmaLabel(t)));
    return m;
  }, [turmas.data]);

  return (
    <section className="cartao">
      <h2>Matrículas</h2>
      {matriculas.isLoading && <p>Carregando…</p>}
      {matriculas.isError && <p className="erro">Falha ao carregar matrículas.</p>}
      {matriculas.data && matriculas.data.length === 0 && <p>Nenhuma matrícula.</p>}
      {matriculas.data && matriculas.data.length > 0 && (
        <table>
          <thead>
            <tr>
              <th>Aluno</th>
              <th>Turma</th>
              <th>Situação</th>
            </tr>
          </thead>
          <tbody>
            {matriculas.data.map((m) => (
              <tr key={m.id}>
                <td>{m.aluno_nome}</td>
                <td>{mapaTurma.get(m.turma_id) ?? m.turma_id.slice(0, 8)}</td>
                <td>{m.situacao}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}

function NovaMatricula() {
  const pessoas = usePessoas();
  const turmas = useTurmas();
  const criar = useCriarMatricula();
  const [alunoId, setAlunoId] = useState("");
  const [turmaId, setTurmaId] = useState("");
  const [comCobranca, setComCobranca] = useState(false);
  const [valor, setValor] = useState("");
  const [competencia, setCompetencia] = useState("");
  const [vencimento, setVencimento] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setErro(null);
    setOk(null);
    try {
      await criar.mutateAsync({
        aluno_id: alunoId,
        turma_id: turmaId,
        cobranca_inicial: comCobranca
          ? { valor: Number(valor), competencia, vencimento }
          : undefined,
      });
      setOk(
        comCobranca
          ? "Matrícula criada com cobrança inicial."
          : "Matrícula criada.",
      );
      setAlunoId("");
      setTurmaId("");
      setComCobranca(false);
      setValor("");
      setCompetencia("");
      setVencimento("");
    } catch (err) {
      setErro(err instanceof ApiError ? err.message : "Falha ao matricular.");
    }
  }

  return (
    <section className="cartao">
      <h2>Nova matrícula</h2>
      <form className="form" onSubmit={onSubmit}>
        <label>
          Aluno
          <select value={alunoId} onChange={(e) => setAlunoId(e.target.value)} required>
            <option value="" disabled>
              Selecione…
            </option>
            {pessoas.data?.map((p) => (
              <option key={p.id} value={p.id}>
                {p.nome}
              </option>
            ))}
          </select>
        </label>
        <label>
          Turma
          <select value={turmaId} onChange={(e) => setTurmaId(e.target.value)} required>
            <option value="" disabled>
              Selecione…
            </option>
            {turmas.data?.map((t) => (
              <option key={t.id} value={t.id}>
                {turmaLabel(t)}
              </option>
            ))}
          </select>
        </label>

        <label className="check">
          <input
            type="checkbox"
            checked={comCobranca}
            onChange={(e) => setComCobranca(e.target.checked)}
          />
          Gerar cobrança inicial (título de mensalidade)
        </label>

        {comCobranca && (
          <div className="itens">
            <div className="linha">
              <label>
                Valor
                <input
                  type="number"
                  step="0.01"
                  min="0.01"
                  value={valor}
                  onChange={(e) => setValor(e.target.value)}
                  required={comCobranca}
                />
              </label>
              <label>
                Competência
                <input
                  type="month"
                  value={competencia}
                  onChange={(e) => setCompetencia(e.target.value)}
                  required={comCobranca}
                />
              </label>
            </div>
            <label>
              Vencimento
              <input
                type="date"
                value={vencimento}
                onChange={(e) => setVencimento(e.target.value)}
                required={comCobranca}
              />
            </label>
            {valor && <p className="sub">Título: {money(Number(valor))}</p>}
          </div>
        )}

        {erro && <p className="erro">{erro}</p>}
        {ok && <p className="ok">{ok}</p>}
        <button type="submit" disabled={criar.isPending}>
          {criar.isPending ? "Matriculando…" : "Matricular"}
        </button>
      </form>
    </section>
  );
}
