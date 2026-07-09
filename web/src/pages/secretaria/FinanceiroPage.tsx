import { useState, type FormEvent } from "react";
import { ApiError } from "../../lib/api";
import { money } from "../../lib/format";
import {
  useCriarTitulo,
  usePagamentos,
  usePessoas,
  useRegistrarPagamento,
  useTitulos,
  type ItemInput,
} from "../../features/secretaria/api";
import type { Titulo } from "../../types";

const STATUS = [
  { valor: "", rotulo: "Todos" },
  { valor: "pendente", rotulo: "Pendentes" },
  { valor: "parcial", rotulo: "Parciais" },
  { valor: "liquidado", rotulo: "Liquidados" },
];

export function FinanceiroPage() {
  const [status, setStatus] = useState("");
  const [selecionado, setSelecionado] = useState<Titulo | null>(null);
  const titulos = useTitulos(status);

  return (
    <div className="fin-grade">
      <section className="cartao">
        <div className="cartao-cab">
          <h2>Títulos</h2>
          <select value={status} onChange={(e) => setStatus(e.target.value)}>
            {STATUS.map((s) => (
              <option key={s.valor} value={s.valor}>
                {s.rotulo}
              </option>
            ))}
          </select>
        </div>
        {titulos.isLoading && <p>Carregando…</p>}
        {titulos.isError && <p className="erro">Falha ao carregar títulos.</p>}
        {titulos.data && titulos.data.length === 0 && <p>Nenhum título.</p>}
        {titulos.data && titulos.data.length > 0 && (
          <table>
            <thead>
              <tr>
                <th>Aluno</th>
                <th>Comp.</th>
                <th>Total</th>
                <th>Saldo</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {titulos.data.map((t) => (
                <tr
                  key={t.id}
                  className={selecionado?.id === t.id ? "sel" : "clicavel"}
                  onClick={() => setSelecionado(t)}
                >
                  <td>{t.aluno_nome}</td>
                  <td>{t.competencia}</td>
                  <td>{money(t.valor_total)}</td>
                  <td>{money(t.saldo)}</td>
                  <td>
                    <StatusTag valor={t.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <div className="fin-lado">
        <NovoTitulo />
        {selecionado && (
          <TituloDetalhe
            titulo={selecionado}
            aoAtualizar={(t) => setSelecionado(t)}
          />
        )}
      </div>
    </div>
  );
}

function NovoTitulo() {
  const pessoas = usePessoas();
  const criar = useCriarTitulo();
  const [alunoId, setAlunoId] = useState("");
  const [competencia, setCompetencia] = useState("");
  const [vencimento, setVencimento] = useState("");
  const [descricao, setDescricao] = useState("");
  const [itens, setItens] = useState<ItemInput[]>([{ descricao: "", valor: 0 }]);
  const [erro, setErro] = useState<string | null>(null);
  const [ok, setOk] = useState(false);

  function setItem(i: number, campo: keyof ItemInput, valor: string) {
    setItens((xs) =>
      xs.map((it, idx) =>
        idx === i
          ? { ...it, [campo]: campo === "valor" ? Number(valor) : valor }
          : it,
      ),
    );
  }

  const total = itens.reduce((s, it) => s + (it.valor || 0), 0);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setErro(null);
    setOk(false);
    try {
      await criar.mutateAsync({
        aluno_id: alunoId,
        competencia,
        vencimento,
        descricao: descricao || undefined,
        itens,
      });
      setOk(true);
      setDescricao("");
      setItens([{ descricao: "", valor: 0 }]);
      setCompetencia("");
      setVencimento("");
    } catch (err) {
      setErro(err instanceof ApiError ? err.message : "Falha ao criar título.");
    }
  }

  return (
    <section className="cartao">
      <h2>Novo título</h2>
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
        <div className="linha">
          <label>
            Competência
            <input
              type="month"
              value={competencia}
              onChange={(e) => setCompetencia(e.target.value)}
              required
            />
          </label>
          <label>
            Vencimento
            <input
              type="date"
              value={vencimento}
              onChange={(e) => setVencimento(e.target.value)}
              required
            />
          </label>
        </div>
        <label>
          Descrição (opcional)
          <input value={descricao} onChange={(e) => setDescricao(e.target.value)} />
        </label>

        <div className="itens">
          <span className="sub">Itens</span>
          {itens.map((it, i) => (
            <div className="linha item" key={i}>
              <input
                placeholder="Descrição (ex.: MENSALIDADE)"
                value={it.descricao}
                onChange={(e) => setItem(i, "descricao", e.target.value)}
                required
              />
              <input
                type="number"
                step="0.01"
                min="0.01"
                placeholder="Valor"
                value={it.valor || ""}
                onChange={(e) => setItem(i, "valor", e.target.value)}
                required
              />
              {itens.length > 1 && (
                <button
                  type="button"
                  className="link"
                  onClick={() => setItens((xs) => xs.filter((_, idx) => idx !== i))}
                >
                  remover
                </button>
              )}
            </div>
          ))}
          <button
            type="button"
            className="link"
            onClick={() => setItens((xs) => [...xs, { descricao: "", valor: 0 }])}
          >
            + adicionar item
          </button>
        </div>

        <p className="sub">Total: {money(total)}</p>
        {erro && <p className="erro">{erro}</p>}
        {ok && <p className="ok">Título criado.</p>}
        <button type="submit" disabled={criar.isPending}>
          {criar.isPending ? "Salvando…" : "Criar título"}
        </button>
      </form>
    </section>
  );
}

function TituloDetalhe({
  titulo,
  aoAtualizar,
}: {
  titulo: Titulo;
  aoAtualizar: (t: Titulo) => void;
}) {
  const pagamentos = usePagamentos(titulo.id);
  const pagar = useRegistrarPagamento(titulo.id);
  const [valor, setValor] = useState("");
  const [data, setData] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const saldo = Number(titulo.saldo);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setErro(null);
    try {
      await pagar.mutateAsync({
        valor: Number(valor),
        data_pagamento: data || undefined,
      });
      // Atualiza o card com o novo saldo/status (recalculado no servidor).
      const novoPago = Number(titulo.total_pago) + Number(valor);
      const novoSaldo = Number(titulo.valor_total) - novoPago;
      aoAtualizar({
        ...titulo,
        total_pago: String(novoPago),
        saldo: String(novoSaldo),
        status: novoSaldo <= 0 ? "liquidado" : "parcial",
      });
      setValor("");
      setData("");
    } catch (err) {
      setErro(err instanceof ApiError ? err.message : "Falha ao registrar pagamento.");
    }
  }

  return (
    <section className="cartao">
      <h2>
        {titulo.aluno_nome} · {titulo.competencia}
      </h2>
      <p className="sub">
        Total {money(titulo.valor_total)} · Pago {money(titulo.total_pago)} · Saldo{" "}
        {money(titulo.saldo)} · <StatusTag valor={titulo.status} />
      </p>

      <table>
        <thead>
          <tr>
            <th>Item</th>
            <th>Valor</th>
          </tr>
        </thead>
        <tbody>
          {titulo.itens.map((it) => (
            <tr key={it.id}>
              <td>{it.descricao}</td>
              <td>{money(it.valor)}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h3>Pagamentos</h3>
      {pagamentos.data && pagamentos.data.length === 0 && <p className="sub">Nenhum.</p>}
      <ul className="lista-simples">
        {pagamentos.data?.map((p) => (
          <li key={p.id}>
            {p.data_pagamento} — {money(p.valor)}
          </li>
        ))}
      </ul>

      {saldo > 0 ? (
        <form className="form" onSubmit={onSubmit}>
          <div className="linha">
            <label>
              Valor
              <input
                type="number"
                step="0.01"
                min="0.01"
                max={saldo}
                value={valor}
                onChange={(e) => setValor(e.target.value)}
                required
              />
            </label>
            <label>
              Data (opcional)
              <input type="date" value={data} onChange={(e) => setData(e.target.value)} />
            </label>
          </div>
          {erro && <p className="erro">{erro}</p>}
          <button type="submit" disabled={pagar.isPending}>
            {pagar.isPending ? "Registrando…" : "Registrar pagamento"}
          </button>
        </form>
      ) : (
        <p className="ok">Título liquidado.</p>
      )}
    </section>
  );
}

function StatusTag({ valor }: { valor: string }) {
  const cls =
    valor === "liquidado" ? "tag ok" : valor === "parcial" ? "tag neutra" : "tag ruim";
  return <span className={cls}>{valor}</span>;
}
