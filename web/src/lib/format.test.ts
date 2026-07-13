import { describe, expect, it } from "vitest";
import { money } from "./format";

describe("money", () => {
  it("formata string decimal da API como BRL", () => {
    expect(money("700.50")).toContain("700,50");
    expect(money("700.50")).toContain("R$");
  });

  it("formata número", () => {
    expect(money(0)).toContain("0,00");
    expect(money(1234.5)).toContain("1.234,50");
  });
});
