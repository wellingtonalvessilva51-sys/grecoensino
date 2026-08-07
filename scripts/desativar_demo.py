"""Desativa logins demo numa base que virou produção.

O deploy antigo rodava `seed_dev` a cada boot, deixando usuários com senha
conhecida (`admin@escola-a.dev` etc.) na base. Este script os desativa
(`ativo=False`) e revoga as sessões abertas — sem apagar nada, então o
histórico acadêmico/financeiro criado por eles continua íntegro e auditável.

Por padrão só MOSTRA o que faria. Use `--aplicar` para gravar.

Uso:
    venv\\Scripts\\python.exe -m scripts.desativar_demo             # dry-run
    venv\\Scripts\\python.exe -m scripts.desativar_demo --aplicar
    ... --sufixo @escola-a.dev --aplicar        # restringe a um domínio
"""

import argparse
import sys

from sqlalchemy import select

from src.core.database import SessionLocal
from src.core.tenancy import reset_current_tenant, set_current_tenant
from src.modules.identidade import service as identidade
from src.modules.identidade.models import Usuario
from src.modules.tenancy import service as tenancy

# Domínios usados pelo seed demo.
SUFIXOS_DEMO = ("@escola-a.dev", "@escola-b.dev")


def _argumentos(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Desativa usuários demo (dry-run por padrão).")
    p.add_argument(
        "--sufixo",
        action="append",
        dest="sufixos",
        help="Sufixo de e-mail a desativar (repetível). Default: domínios do seed demo.",
    )
    p.add_argument(
        "--aplicar",
        action="store_true",
        help="Grava as mudanças. Sem esta flag, apenas lista.",
    )
    return p.parse_args(argv)


def usuarios_demo(db, sufixos: tuple[str, ...]) -> list[Usuario]:
    """Usuários ativos cujo e-mail casa com algum sufixo demo (tenant do contexto)."""
    todos = db.scalars(
        select(Usuario).where(Usuario.ativo.is_(True), Usuario.deleted_at.is_(None))
    ).all()
    return [u for u in todos if u.email.endswith(sufixos)]


def main(argv: list[str] | None = None) -> int:
    args = _argumentos(argv)
    sufixos = tuple(args.sufixos) if args.sufixos else SUFIXOS_DEMO
    total = 0

    with SessionLocal() as db:
        for tenant in tenancy.listar(db):
            token = set_current_tenant(tenant.id)
            try:
                alvos = usuarios_demo(db, sufixos)
                if not alvos:
                    continue
                print(f"\ntenant {tenant.subdominio} ({tenant.id}):")
                for usuario in alvos:
                    total += 1
                    if args.aplicar:
                        usuario.ativo = False
                        identidade.revogar_todas(db, usuario.id)  # faz commit
                        print(f"  desativado: {usuario.email}")
                    else:
                        print(f"  seria desativado: {usuario.email}")
                if args.aplicar:
                    db.commit()
            finally:
                reset_current_tenant(token)

    if total == 0:
        print(f"Nenhum usuário ativo com os sufixos {sufixos}.")
    elif args.aplicar:
        print(f"\n{total} usuário(s) demo desativado(s) e com sessões revogadas.")
    else:
        print(f"\n{total} usuário(s) seriam desativados. Rode com --aplicar para gravar.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
