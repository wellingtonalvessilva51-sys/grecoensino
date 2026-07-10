import { Navigate, Route, Routes } from "react-router-dom";
import type { ReactNode } from "react";
import { LoginPage } from "./pages/LoginPage";
import { PortalResponsavel } from "./pages/PortalResponsavel";
import { SecretariaLayout } from "./pages/secretaria/SecretariaLayout";
import { FinanceiroPage } from "./pages/secretaria/FinanceiroPage";
import { AlunosMatriculasPage } from "./pages/secretaria/AlunosMatriculasPage";
import { CadastrosPage } from "./pages/secretaria/CadastrosPage";
import { LancamentoPage } from "./pages/secretaria/LancamentoPage";
import { RecadosPage } from "./pages/secretaria/RecadosPage";
import { ProtectedRoute } from "./routes/ProtectedRoute";
import { useAuth } from "./lib/auth";
import { ehSecretaria, rotaInicial } from "./lib/roles";

/** "/" decide o destino conforme o papel do usuário. */
function RoleLanding() {
  const { user, carregando } = useAuth();
  if (carregando) return <div className="tela-centro">Carregando…</div>;
  if (!user) return <Navigate to="/login" replace />;
  return <Navigate to={rotaInicial(user)} replace />;
}

/** Restringe uma rota aos papéis administrativos. */
function ApenasSecretaria({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  if (!ehSecretaria(user)) return <Navigate to="/portal" replace />;
  return <>{children}</>;
}

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/" element={<RoleLanding />} />

      <Route
        path="/portal"
        element={
          <ProtectedRoute>
            <PortalResponsavel />
          </ProtectedRoute>
        }
      />

      <Route
        path="/secretaria"
        element={
          <ProtectedRoute>
            <ApenasSecretaria>
              <SecretariaLayout />
            </ApenasSecretaria>
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="financeiro" replace />} />
        <Route path="financeiro" element={<FinanceiroPage />} />
        <Route path="alunos" element={<AlunosMatriculasPage />} />
        <Route path="lancamento" element={<LancamentoPage />} />
        <Route path="recados" element={<RecadosPage />} />
        <Route path="cadastros" element={<CadastrosPage />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
