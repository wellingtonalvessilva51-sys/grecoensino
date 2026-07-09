// Cliente HTTP fino sobre fetch: injeta Authorization + X-Tenant-ID, trata o
// envelope de erro do backend ({erro:{codigo,mensagem}}) e faz UM refresh
// automático de token no 401 antes de remeter a requisição.

import { API_BASE_URL, DEV_TENANT_ID } from "./config";
import {
  clearTokens,
  getAccessToken,
  getRefreshToken,
  setTokens,
} from "./tokens";
import type { TokenResposta } from "../types";

export class ApiError extends Error {
  status: number;
  codigo: string;
  constructor(status: number, codigo: string, mensagem: string) {
    super(mensagem);
    this.status = status;
    this.codigo = codigo;
  }
}

/** Erro de autenticação: caller deve mandar o usuário para o login. */
export class NaoAutenticado extends ApiError {}

function baseHeaders(withAuth: boolean): Record<string, string> {
  const h: Record<string, string> = { "Content-Type": "application/json" };
  if (DEV_TENANT_ID) h["X-Tenant-ID"] = DEV_TENANT_ID;
  if (withAuth) {
    const access = getAccessToken();
    if (access) h["Authorization"] = `Bearer ${access}`;
  }
  return h;
}

async function parse(resp: Response): Promise<unknown> {
  if (resp.status === 204) return null;
  const texto = await resp.text();
  return texto ? JSON.parse(texto) : null;
}

function extrairErro(status: number, corpo: unknown): ApiError {
  const erro = (corpo as { erro?: { codigo?: string; mensagem?: string } })
    ?.erro;
  const codigo = erro?.codigo ?? "erro";
  const mensagem = erro?.mensagem ?? "Falha na requisição.";
  return status === 401
    ? new NaoAutenticado(status, codigo, mensagem)
    : new ApiError(status, codigo, mensagem);
}

/** Tenta rotacionar a sessão. Retorna true se conseguiu novo access token. */
async function tentarRefresh(): Promise<boolean> {
  const refresh = getRefreshToken();
  if (!refresh) return false;
  const resp = await fetch(`${API_BASE_URL}/v1/auth/refresh`, {
    method: "POST",
    headers: baseHeaders(false),
    body: JSON.stringify({ refresh_token: refresh }),
  });
  if (!resp.ok) return false;
  const tokens = (await parse(resp)) as TokenResposta;
  setTokens(tokens.access_token, tokens.refresh_token);
  return true;
}

export interface RequestOptions {
  method?: string;
  body?: unknown;
  auth?: boolean; // default: true
}

export async function apiFetch<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const { method = "GET", body, auth = true } = options;
  const url = `${API_BASE_URL}/v1${path}`;
  const init: RequestInit = {
    method,
    headers: baseHeaders(auth),
    body: body !== undefined ? JSON.stringify(body) : undefined,
  };

  let resp = await fetch(url, init);

  // 401 em rota autenticada → tenta um refresh e remete uma única vez.
  if (resp.status === 401 && auth && getRefreshToken()) {
    const ok = await tentarRefresh();
    if (ok) {
      init.headers = baseHeaders(auth);
      resp = await fetch(url, init);
    }
  }

  const corpo = await parse(resp);
  if (!resp.ok) {
    const erro = extrairErro(resp.status, corpo);
    if (erro instanceof NaoAutenticado) clearTokens();
    throw erro;
  }
  return corpo as T;
}
