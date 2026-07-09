import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../../lib/auth";

export function SecretariaLayout() {
  const { user, sair } = useAuth();
  return (
    <div className="pagina">
      <header className="topo">
        <div className="topo-esq">
          <strong>Gestão Educacional</strong>
          <span className="sub"> · Secretaria</span>
          <nav className="nav">
            <NavLink to="/secretaria/alunos">Alunos & Matrículas</NavLink>
            <NavLink to="/secretaria/financeiro">Financeiro</NavLink>
          </nav>
        </div>
        <div className="topo-dir">
          <span>{user?.nome}</span>
          <button className="link" onClick={() => void sair()}>
            Sair
          </button>
        </div>
      </header>
      <main className="conteudo">
        <Outlet />
      </main>
    </div>
  );
}
