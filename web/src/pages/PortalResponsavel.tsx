import { useState } from "react";
import { useAuth } from "../lib/auth";
import {
  useBoletim,
  useFrequenciaResumo,
  useMarcarRecadoLido,
  useMatriculas,
  useRecados,
  useTitulos,
} from "../features/responsavel/api";
import type { Titulo } from "../types";

const REAIS = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
});

function money(v: string): string {
  return REAIS.format(Number(v));
}

export function PortalResponsavel() {
  const { user, sair } = useAuth();
  const matriculas = useMatriculas();
  const [matriculaId, setMatriculaId] = useState<string | undefined>();

  // Seleciona a primeira matrícula assim que a lista chega.
  const lista = matriculas.data ?? [];
  const atual = matriculaId ?? lista[0]?.id;

  return (
    <div className="pagina">
      <header className="topo">
        <div>
          <strong>Gestão Educacional</strong>
          <span className="sub"> · Portal do Responsável</span>
        </div>
        <div className="topo-dir">
          <span>{user?.nome}</span>
          <button className="link" onClick={() => void sair()}>
            Sair
          </button>
        </div>
      </header>

      <main className="conteudo">
        {matriculas.isLoading && <p>Carregando matrículas…</p>}
        {matriculas.isError && (
          <p className="erro">Não foi possível carregar as matrículas.</p>
        )}
        {!matriculas.isLoading && lista.length === 0 && (
          <p>Nenhuma matrícula vinculada a este responsável.</p>
        )}

        {lista.length > 1 && (
          <label className="seletor">
            Dependente / turma
            <select
              value={atual}
              onChange={(e) => setMatriculaId(e.target.value)}
            >
              {lista.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.aluno_id.slice(0, 8)} · {m.situacao}
                </option>
              ))}
            </select>
          </label>
        )}

        {atual && (
          <div className="grade">
            <BoletimCard matriculaId={atual} />
            <FrequenciaCard matriculaId={atual} />
            <FinanceiroCard />
            <RecadosCard />
          </div>
        )}
      </main>
    </div>
  );
}

function BoletimCard({ matriculaId }: { matriculaId: string }) {
  const { data, isLoading, isError } = useBoletim(matriculaId);
  return (
    <section className="cartao">
      <h2>Boletim</h2>
      {isLoading && <p>Carregando…</p>}
      {isError && <p className="erro">Falha ao carregar o boletim.</p>}
      {data && (
        <>
          <p>
            Situação final: <SituacaoTag valor={data.situacao_final} />
          </p>
          <table>
            <thead>
              <tr>
                <th>Disciplina</th>
                <th>Média</th>
                <th>Situação</th>
              </tr>
            </thead>
            <tbody>
              {data.disciplinas.map((d) => (
                <tr key={d.disciplina_id}>
                  <td>{d.disciplina_id.slice(0, 8)}</td>
                  <td>{d.media}</td>
                  <td>
                    <SituacaoTag valor={d.situacao} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="sub">
            Média mínima {data.media_minima} · {data.num_periodos} períodos
          </p>
        </>
      )}
    </section>
  );
}

function FrequenciaCard({ matriculaId }: { matriculaId: string }) {
  const { data, isLoading, isError } = useFrequenciaResumo(matriculaId);
  return (
    <section className="cartao">
      <h2>Frequência</h2>
      {isLoading && <p>Carregando…</p>}
      {isError && <p className="erro">Falha ao carregar a frequência.</p>}
      {data && (
        <>
          <p className="grande">{data.percentual}%</p>
          <p className={data.suficiente ? "ok" : "erro"}>
            {data.suficiente ? "Frequência suficiente" : "Abaixo do mínimo"} (mín.{" "}
            {data.frequencia_minima}%)
          </p>
          <p className="sub">
            {data.presencas} presenças / {data.dias_letivos} dias · {data.faltas}{" "}
            faltas ({data.faltas_justificadas} justificadas)
          </p>
        </>
      )}
    </section>
  );
}

function FinanceiroCard() {
  const { data, isLoading, isError } = useTitulos();
  return (
    <section className="cartao">
      <h2>Financeiro</h2>
      {isLoading && <p>Carregando…</p>}
      {isError && <p className="erro">Falha ao carregar os títulos.</p>}
      {data && data.length === 0 && <p>Nenhum título.</p>}
      {data && data.length > 0 && (
        <table>
          <thead>
            <tr>
              <th>Competência</th>
              <th>Vencimento</th>
              <th>Total</th>
              <th>Saldo</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {data.map((t: Titulo) => (
              <tr key={t.id}>
                <td>{t.competencia}</td>
                <td>{t.vencimento}</td>
                <td>{money(t.valor_total)}</td>
                <td>{money(t.saldo)}</td>
                <td>
                  <StatusTitulo valor={t.status} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}

function RecadosCard() {
  const { data, isLoading, isError } = useRecados();
  const marcar = useMarcarRecadoLido();
  return (
    <section className="cartao">
      <h2>Recados</h2>
      {isLoading && <p>Carregando…</p>}
      {isError && <p className="erro">Falha ao carregar os recados.</p>}
      {data && data.length === 0 && <p>Sem recados.</p>}
      <ul className="recados">
        {data?.map((r) => (
          <li key={r.destinatario_id} className={r.lido_em ? "lido" : "novo"}>
            <div className="recado-cab">
              <strong>{r.titulo}</strong>
              {!r.lido_em && (
                <button
                  className="link"
                  disabled={marcar.isPending}
                  onClick={() => marcar.mutate(r.destinatario_id)}
                >
                  marcar como lido
                </button>
              )}
            </div>
            <p>{r.mensagem}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}

function SituacaoTag({ valor }: { valor: string }) {
  const cls =
    valor === "aprovado"
      ? "tag ok"
      : valor === "cursando"
        ? "tag neutra"
        : "tag ruim";
  return <span className={cls}>{valor.replace("_", " ")}</span>;
}

function StatusTitulo({ valor }: { valor: string }) {
  const cls =
    valor === "liquidado" ? "tag ok" : valor === "parcial" ? "tag neutra" : "tag ruim";
  return <span className={cls}>{valor}</span>;
}
