"""Resolução de tenant (NÃO-NEGOCIÁVEL).

Stub do esqueleto — implementação na fatia de Multi-tenancy (passo 2).

Regras (ver CLAUDE.md §7):
- tenant resolvido no servidor (subdomínio ou claim do JWT), NUNCA por parâmetro
  de URL manipulável pelo cliente;
- toda query filtra por tenant_id, reforçado na camada de acesso a dados;
- testes de "tenant confusion" obrigatórios.
"""

# TODO(tenancy): middleware/dependência que resolve o tenant_id atual e o injeta
# no escopo da request; filtro automático por tenant na camada de dados.
