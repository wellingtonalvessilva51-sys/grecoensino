import { useState, type FormEvent } from "react";
import { ApiError } from "../../lib/api";
import { usePessoas } from "../../features/secretaria/api";
import {
  useCriarRecado,
  useEnviados,
} from "../../features/secretaria/comunicacao";

export function RecadosPage() {
  return (
    <div className="fin-grade">
      <NovoRecado />
      <Enviados />
    </div>
  );
}

function NovoRecado() {
  const pessoas = usePessoas();
  const criar = useCriarRecado();
  const [titulo, setTitulo] = useState("");
  const [mensagem, setMensagem] = useState("");
  const [dest, setDest] = useState<Set<string>>(new Set());
  const [erro, setErro] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);

  function alterna(id: string) {
    setDest((s) => {
      const novo = new Set(s);
      if (novo.has(id)) novo.delete(id);
      else novo.add(id);
      return novo;
    });
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setErro(null);
    setOk(null);
    if (dest.size === 0) {
      setErro("Selecione ao menos um destinatário.");
      return;
    }
    try {
      const r = await criar.mutateAsync({
        titulo,
        mensagem,
        destinatarios: [...dest],
      });
      setOk(`Recado enviado para ${r.total_destinatarios} destinatário(s).`);
      setTitulo("");
      setMensagem("");
      setDest(new Set());
    } catch (err) {
      setErro(err instanceof ApiError ? err.message : "Falha ao enviar recado.");
    }
  }

  return (
    <section className="cartao">
      <h2>Novo recado</h2>
      <form className="form" onSubmit={onSubmit}>
        <label>
          Título
          <input value={titulo} onChange={(e) => setTitulo(e.target.value)} required />
        </label>
        <label>
          Mensagem
          <textarea
            value={mensagem}
            onChange={(e) => setMensagem(e.target.value)}
            rows={4}
            required
          />
        </label>

        <div className="itens">
          <span className="sub">Destinatários ({dest.size} selecionados)</span>
          <div className="checklist">
            {pessoas.data?.map((p) => (
              <label key={p.id} className="check">
                <input
                  type="checkbox"
                  checked={dest.has(p.id)}
                  onChange={() => alterna(p.id)}
                />
                {p.nome}
              </label>
            ))}
          </div>
        </div>

        {erro && <p className="erro">{erro}</p>}
        {ok && <p className="ok">{ok}</p>}
        <button type="submit" disabled={criar.isPending}>
          {criar.isPending ? "Enviando…" : "Enviar recado"}
        </button>
      </form>
    </section>
  );
}

function Enviados() {
  const enviados = useEnviados();
  return (
    <section className="cartao">
      <h2>Enviados</h2>
      {enviados.isLoading && <p>Carregando…</p>}
      {enviados.isError && <p className="erro">Falha ao carregar enviados.</p>}
      {enviados.data && enviados.data.length === 0 && <p>Nenhum recado enviado.</p>}
      <ul className="recados">
        {enviados.data?.map((r) => (
          <li key={r.id}>
            <div className="recado-cab">
              <strong>{r.titulo}</strong>
              <span className="sub">{r.total_destinatarios} destinatário(s)</span>
            </div>
            <p>{r.mensagem}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}
