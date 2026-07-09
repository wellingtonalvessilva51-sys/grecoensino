import { useMemo, useState, type FormEvent, type ReactNode } from "react";
import { ApiError } from "../../lib/api";
import { usePessoas, useTurmas } from "../../features/secretaria/api";
import {
  useAnosLetivos,
  useAtribuicoes,
  useCriarAnoLetivo,
  useCriarAtribuicao,
  useCriarCurso,
  useCriarDisciplina,
  useCriarSerie,
  useCriarTurma,
  useCursos,
  useDisciplinas,
  useSeries,
} from "../../features/secretaria/cadastros";

export function CadastrosPage() {
  return (
    <div className="grade">
      <AnosLetivos />
      <Cursos />
      <Series />
      <Disciplinas />
      <Turmas />
      <Atribuicoes />
    </div>
  );
}

/** Casca de formulário: cuida de erro/ok e do submit. */
function Form({
  onSubmit,
  children,
  pendente,
  rotulo,
}: {
  onSubmit: () => Promise<void>;
  children: ReactNode;
  pendente: boolean;
  rotulo: string;
}) {
  const [erro, setErro] = useState<string | null>(null);
  const [ok, setOk] = useState(false);
  async function handle(e: FormEvent) {
    e.preventDefault();
    setErro(null);
    setOk(false);
    try {
      await onSubmit();
      setOk(true);
    } catch (err) {
      setErro(err instanceof ApiError ? err.message : "Falha ao salvar.");
    }
  }
  return (
    <form className="form" onSubmit={handle}>
      {children}
      {erro && <p className="erro">{erro}</p>}
      {ok && <p className="ok">Salvo.</p>}
      <button type="submit" disabled={pendente}>
        {pendente ? "Salvando…" : rotulo}
      </button>
    </form>
  );
}

function AnosLetivos() {
  const lista = useAnosLetivos();
  const criar = useCriarAnoLetivo();
  const [ano, setAno] = useState("");
  const [descricao, setDescricao] = useState("");
  return (
    <section className="cartao">
      <h2>Anos letivos</h2>
      <ul className="lista-simples">
        {lista.data?.map((a) => (
          <li key={a.id}>
            {a.ano} · {a.situacao}
            {a.descricao ? ` · ${a.descricao}` : ""}
          </li>
        ))}
      </ul>
      <Form
        pendente={criar.isPending}
        rotulo="Adicionar ano"
        onSubmit={async () => {
          await criar.mutateAsync({ ano: Number(ano), descricao: descricao || undefined });
          setAno("");
          setDescricao("");
        }}
      >
        <div className="linha">
          <label>
            Ano
            <input
              type="number"
              value={ano}
              onChange={(e) => setAno(e.target.value)}
              required
            />
          </label>
          <label>
            Descrição
            <input value={descricao} onChange={(e) => setDescricao(e.target.value)} />
          </label>
        </div>
      </Form>
    </section>
  );
}

function Cursos() {
  const lista = useCursos();
  const criar = useCriarCurso();
  const [nome, setNome] = useState("");
  const [codigo, setCodigo] = useState("");
  return (
    <section className="cartao">
      <h2>Cursos</h2>
      <ul className="lista-simples">
        {lista.data?.map((c) => (
          <li key={c.id}>
            {c.nome}
            {c.codigo ? ` · ${c.codigo}` : ""}
          </li>
        ))}
      </ul>
      <Form
        pendente={criar.isPending}
        rotulo="Adicionar curso"
        onSubmit={async () => {
          await criar.mutateAsync({ nome, codigo: codigo || undefined });
          setNome("");
          setCodigo("");
        }}
      >
        <label>
          Nome
          <input value={nome} onChange={(e) => setNome(e.target.value)} required />
        </label>
        <label>
          Código (opcional)
          <input value={codigo} onChange={(e) => setCodigo(e.target.value)} />
        </label>
      </Form>
    </section>
  );
}

function Series() {
  const lista = useSeries();
  const cursos = useCursos();
  const criar = useCriarSerie();
  const [cursoId, setCursoId] = useState("");
  const [nome, setNome] = useState("");
  const [ordem, setOrdem] = useState("");
  const mapaCurso = useMemo(() => {
    const m = new Map<string, string>();
    cursos.data?.forEach((c) => m.set(c.id, c.nome));
    return m;
  }, [cursos.data]);
  return (
    <section className="cartao">
      <h2>Séries</h2>
      <ul className="lista-simples">
        {lista.data?.map((s) => (
          <li key={s.id}>
            {s.nome} · {mapaCurso.get(s.curso_id) ?? "—"}
          </li>
        ))}
      </ul>
      <Form
        pendente={criar.isPending}
        rotulo="Adicionar série"
        onSubmit={async () => {
          await criar.mutateAsync({
            curso_id: cursoId,
            nome,
            ordem: ordem ? Number(ordem) : undefined,
          });
          setNome("");
          setOrdem("");
        }}
      >
        <label>
          Curso
          <select value={cursoId} onChange={(e) => setCursoId(e.target.value)} required>
            <option value="" disabled>
              Selecione…
            </option>
            {cursos.data?.map((c) => (
              <option key={c.id} value={c.id}>
                {c.nome}
              </option>
            ))}
          </select>
        </label>
        <div className="linha">
          <label>
            Nome
            <input value={nome} onChange={(e) => setNome(e.target.value)} required />
          </label>
          <label>
            Ordem
            <input
              type="number"
              value={ordem}
              onChange={(e) => setOrdem(e.target.value)}
            />
          </label>
        </div>
      </Form>
    </section>
  );
}

function Disciplinas() {
  const lista = useDisciplinas();
  const criar = useCriarDisciplina();
  const [nome, setNome] = useState("");
  const [codigo, setCodigo] = useState("");
  return (
    <section className="cartao">
      <h2>Disciplinas</h2>
      <ul className="lista-simples">
        {lista.data?.map((d) => (
          <li key={d.id}>
            {d.nome}
            {d.codigo ? ` · ${d.codigo}` : ""}
          </li>
        ))}
      </ul>
      <Form
        pendente={criar.isPending}
        rotulo="Adicionar disciplina"
        onSubmit={async () => {
          await criar.mutateAsync({ nome, codigo: codigo || undefined });
          setNome("");
          setCodigo("");
        }}
      >
        <label>
          Nome
          <input value={nome} onChange={(e) => setNome(e.target.value)} required />
        </label>
        <label>
          Código (opcional)
          <input value={codigo} onChange={(e) => setCodigo(e.target.value)} />
        </label>
      </Form>
    </section>
  );
}

function Turmas() {
  const turmas = useTurmas();
  const series = useSeries();
  const anos = useAnosLetivos();
  const criar = useCriarTurma();
  const [serieId, setSerieId] = useState("");
  const [anoId, setAnoId] = useState("");
  const [nome, setNome] = useState("");
  return (
    <section className="cartao">
      <h2>Turmas</h2>
      <ul className="lista-simples">
        {turmas.data?.map((t) => (
          <li key={t.id}>
            {t.serie_nome} · {t.nome} · {t.ano}
          </li>
        ))}
      </ul>
      <Form
        pendente={criar.isPending}
        rotulo="Adicionar turma"
        onSubmit={async () => {
          await criar.mutateAsync({ serie_id: serieId, ano_letivo_id: anoId, nome });
          setNome("");
        }}
      >
        <label>
          Série
          <select value={serieId} onChange={(e) => setSerieId(e.target.value)} required>
            <option value="" disabled>
              Selecione…
            </option>
            {series.data?.map((s) => (
              <option key={s.id} value={s.id}>
                {s.nome}
              </option>
            ))}
          </select>
        </label>
        <div className="linha">
          <label>
            Ano letivo
            <select value={anoId} onChange={(e) => setAnoId(e.target.value)} required>
              <option value="" disabled>
                Selecione…
              </option>
              {anos.data?.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.ano}
                </option>
              ))}
            </select>
          </label>
          <label>
            Nome
            <input value={nome} onChange={(e) => setNome(e.target.value)} required />
          </label>
        </div>
      </Form>
    </section>
  );
}

function Atribuicoes() {
  const turmas = useTurmas();
  const disciplinas = useDisciplinas();
  const pessoas = usePessoas();
  const [turmaId, setTurmaId] = useState("");
  const atribuicoes = useAtribuicoes(turmaId || undefined);
  const criar = useCriarAtribuicao(turmaId);
  const [disciplinaId, setDisciplinaId] = useState("");
  const [professorId, setProfessorId] = useState("");

  const mapaDisc = useMemo(() => {
    const m = new Map<string, string>();
    disciplinas.data?.forEach((d) => m.set(d.id, d.nome));
    return m;
  }, [disciplinas.data]);
  const mapaProf = useMemo(() => {
    const m = new Map<string, string>();
    pessoas.data?.forEach((p) => m.set(p.id, p.nome));
    return m;
  }, [pessoas.data]);

  return (
    <section className="cartao">
      <h2>Disciplinas por turma</h2>
      <label>
        Turma
        <select value={turmaId} onChange={(e) => setTurmaId(e.target.value)}>
          <option value="">Selecione…</option>
          {turmas.data?.map((t) => (
            <option key={t.id} value={t.id}>
              {t.serie_nome} · {t.nome} · {t.ano}
            </option>
          ))}
        </select>
      </label>

      {turmaId && (
        <>
          <ul className="lista-simples">
            {atribuicoes.data?.length === 0 && <li className="sub">Nenhuma.</li>}
            {atribuicoes.data?.map((a) => (
              <li key={a.id}>
                {mapaDisc.get(a.disciplina_id) ?? "—"} ·{" "}
                {mapaProf.get(a.professor_id) ?? "—"}
              </li>
            ))}
          </ul>
          <Form
            pendente={criar.isPending}
            rotulo="Atribuir"
            onSubmit={async () => {
              await criar.mutateAsync({
                disciplina_id: disciplinaId,
                professor_id: professorId,
              });
              setDisciplinaId("");
              setProfessorId("");
            }}
          >
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
                {disciplinas.data?.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.nome}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Professor
              <select
                value={professorId}
                onChange={(e) => setProfessorId(e.target.value)}
                required
              >
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
          </Form>
        </>
      )}
    </section>
  );
}
