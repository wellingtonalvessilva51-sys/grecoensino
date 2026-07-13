import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, NaoAutenticado, apiFetch } from "./api";
import { getAccessToken, setTokens } from "./tokens";

function resp(status: number, body?: unknown): Response {
  return {
    status,
    ok: status >= 200 && status < 400,
    text: async () => (body === undefined ? "" : JSON.stringify(body)),
  } as Response;
}

function fetchMock() {
  const fn = vi.fn();
  globalThis.fetch = fn as unknown as typeof fetch;
  return fn;
}

function ultimoInit(fn: ReturnType<typeof vi.fn>, i = 0) {
  return fn.mock.calls[i][1] as RequestInit & {
    headers: Record<string, string>;
  };
}

beforeEach(() => {
  localStorage.clear();
  vi.restoreAllMocks();
});

describe("apiFetch", () => {
  it("adiciona X-Tenant-ID e Content-Type; monta a URL com /v1", async () => {
    const fn = fetchMock();
    fn.mockResolvedValueOnce(resp(200, { ok: true }));

    await apiFetch("/x", { auth: false });

    expect(fn.mock.calls[0][0]).toBe("http://api.test/v1/x");
    const init = ultimoInit(fn);
    expect(init.method).toBe("GET");
    expect(init.headers["X-Tenant-ID"]).toBe("tenant-123");
    expect(init.headers["Content-Type"]).toBe("application/json");
    expect(init.headers.Authorization).toBeUndefined();
  });

  it("adiciona Authorization quando há access token", async () => {
    const fn = fetchMock();
    setTokens("acc", "ref");
    fn.mockResolvedValueOnce(resp(200, {}));

    await apiFetch("/y");

    expect(ultimoInit(fn).headers.Authorization).toBe("Bearer acc");
  });

  it("lança ApiError com o código do envelope do backend", async () => {
    const fn = fetchMock();
    fn.mockResolvedValueOnce(
      resp(400, { erro: { codigo: "validacao", mensagem: "Dados inválidos." } }),
    );

    try {
      await apiFetch("/z", { auth: false });
      throw new Error("deveria ter lançado");
    } catch (e) {
      expect(e).toBeInstanceOf(ApiError);
      expect((e as ApiError).codigo).toBe("validacao");
      expect((e as ApiError).status).toBe(400);
      expect((e as ApiError).message).toBe("Dados inválidos.");
    }
  });

  it("no 401 tenta refresh e remete a requisição com o novo token", async () => {
    const fn = fetchMock();
    setTokens("old-acc", "old-ref");
    fn.mockResolvedValueOnce(resp(401, { erro: { codigo: "nao_autenticado" } })) // original
      .mockResolvedValueOnce(
        resp(200, {
          access_token: "new-acc",
          refresh_token: "new-ref",
          expira_em_min: 15,
        }),
      ) // refresh
      .mockResolvedValueOnce(resp(200, { data: 1 })); // retry

    const r = await apiFetch<{ data: number }>("/protected");

    expect(r.data).toBe(1);
    expect(fn).toHaveBeenCalledTimes(3);
    expect(fn.mock.calls[1][0]).toBe("http://api.test/v1/auth/refresh");
    expect(getAccessToken()).toBe("new-acc");
    // a remessa usa o token novo
    expect(ultimoInit(fn, 2).headers.Authorization).toBe("Bearer new-acc");
  });

  it("se o refresh falhar, limpa os tokens e lança NaoAutenticado", async () => {
    const fn = fetchMock();
    setTokens("acc", "ref");
    fn.mockResolvedValueOnce(resp(401, { erro: { codigo: "nao_autenticado", mensagem: "expirou" } }))
      .mockResolvedValueOnce(resp(401, {})); // refresh falha

    await expect(apiFetch("/protected")).rejects.toBeInstanceOf(NaoAutenticado);
    expect(getAccessToken()).toBeNull();
  });
});
