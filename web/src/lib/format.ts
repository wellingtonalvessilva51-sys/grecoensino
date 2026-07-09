const REAIS = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
});

/** Formata um valor (string decimal da API ou número) como moeda BRL. */
export function money(v: string | number): string {
  return REAIS.format(Number(v));
}
