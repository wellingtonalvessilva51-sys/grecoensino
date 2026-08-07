"""Bootstrap de produção: cria a escola real e o primeiro admin, sem dado demo.

Contraparte segura do `scripts.seed_dev`: nenhum usuário de vitrine, nenhuma
senha conhecida no código. Idempotente — rodar de novo não recria nem
sobrescreve nada (a senha de um admin existente NÃO é alterada aqui).

Uso (local):
    venv\\Scripts\\python.exe -m scripts.bootstrap_prod \\
        --escola "Colégio Exemplo" --subdominio colegio-exemplo \\
        --admin-email diretoria@colegioexemplo.com.br

Uso (Railway / container) — tudo por variável de ambiente:
    BOOTSTRAP_ESCOLA="Colégio Exemplo"
    BOOTSTRAP_SUBDOMINIO=colegio-exemplo
    BOOTSTRAP_ADMIN_EMAIL=diretoria@colegioexemplo.com.br
    BOOTSTRAP_ADMIN_NOME="Diretoria"           (opcional)
    BOOTSTRAP_ADMIN_SENHA=<senha forte>        (opcional: se ausente, é gerada)
    BOOTSTRAP_TENANT_ID=<uuid fixo>            (opcional: default = DEMO_TENANT_ID)

Se a senha não for informada, uma senha forte é GERADA e impressa uma única vez
na saída do comando — copie e troque no primeiro acesso.
"""

import argparse
import os
import secrets
import sys
import uuid

from src.core.config import settings
from src.core.database import SessionLocal
from src.core.tenancy import reset_current_tenant, set_current_tenant
from src.modules.academico import service as academico
from src.modules.identidade import service as identidade
from src.modules.identidade.schemas import UsuarioCreate
from src.modules.tenancy import service as tenancy
from src.modules.tenancy.models import Tenant
from src.modules.tenancy.schemas import TenantCreate

SENHA_TAMANHO_MINIMO = 12


def _argumentos(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Cria a escola e o admin reais (produção).")
    p.add_argument("--escola", default=os.environ.get("BOOTSTRAP_ESCOLA"))
    p.add_argument("--subdominio", default=os.environ.get("BOOTSTRAP_SUBDOMINIO"))
    p.add_argument("--admin-email", default=os.environ.get("BOOTSTRAP_ADMIN_EMAIL"))
    p.add_argument(
        "--admin-nome", default=os.environ.get("BOOTSTRAP_ADMIN_NOME", "Administrador")
    )
    p.add_argument(
        "--tenant-id",
        default=os.environ.get("BOOTSTRAP_TENANT_ID") or settings.demo_tenant_id,
        help="UUID fixo do tenant. Default: DEMO_TENANT_ID (o id que o front injeta).",
    )
    args = p.parse_args(argv)

    faltando = [
        nome
        for nome, valor in (
            ("--escola / BOOTSTRAP_ESCOLA", args.escola),
            ("--subdominio / BOOTSTRAP_SUBDOMINIO", args.subdominio),
            ("--admin-email / BOOTSTRAP_ADMIN_EMAIL", args.admin_email),
        )
        if not valor
    ]
    if faltando:
        p.error("faltam parâmetros obrigatórios: " + ", ".join(faltando))
    return args


def resolver_senha() -> tuple[str, bool]:
    """Devolve (senha, foi_gerada). Senha informada precisa ser minimamente forte."""
    senha = os.environ.get("BOOTSTRAP_ADMIN_SENHA")
    if not senha:
        return secrets.token_urlsafe(16), True
    if len(senha) < SENHA_TAMANHO_MINIMO:
        raise SystemExit(
            f"BOOTSTRAP_ADMIN_SENHA muito curta (mínimo {SENHA_TAMANHO_MINIMO} caracteres)."
        )
    return senha, False


def obter_ou_criar_tenant(db, nome: str, subdominio: str, tenant_id: str | None) -> Tenant:
    tenant = tenancy.buscar_por_subdominio(db, subdominio)
    if tenant is not None:
        print(f"escola já existe: {tenant.subdominio} ({tenant.id})")
        return tenant

    if tenant_id:
        # Id fixo: o front single-service injeta esse UUID via window.__ENV__,
        # então o tenant precisa nascer com ele para o header casar.
        tenant = Tenant(id=uuid.UUID(tenant_id), nome=nome, subdominio=subdominio)
        db.add(tenant)
        db.commit()
        db.refresh(tenant)
    else:
        tenant = tenancy.criar_tenant(db, TenantCreate(nome=nome, subdominio=subdominio))
    print(f"escola criada:   {tenant.subdominio} ({tenant.id})")
    return tenant


def main(argv: list[str] | None = None) -> int:
    args = _argumentos(argv)
    email = args.admin_email.strip().lower()

    with SessionLocal() as db:
        identidade.garantir_papeis_catalogo(db)
        tenant = obter_ou_criar_tenant(db, args.escola, args.subdominio, args.tenant_id)
        # Guarda o id agora: commits posteriores expiram o objeto, que fica
        # inacessível depois que a sessão fecha.
        tenant_id = tenant.id

        token = set_current_tenant(tenant_id)
        try:
            academico.obter_ou_criar_config(db)

            if identidade.buscar_usuario_por_email(db, email) is not None:
                print(f"admin já existe: {email} (senha inalterada)")
                print("\nNada a fazer. Bootstrap é idempotente.")
                return 0

            senha, gerada = resolver_senha()
            identidade.criar_usuario(
                db,
                UsuarioCreate(
                    nome=args.admin_nome,
                    email=email,
                    senha=senha,
                    papeis=["admin_tenant"],
                ),
            )
        finally:
            reset_current_tenant(token)

    print(f"admin criado:    {email}")
    if gerada:
        print("\n" + "=" * 60)
        print("SENHA GERADA (aparece só agora — copie e guarde):")
        print(f"    {senha}")
        print("=" * 60)
    print(f"\nDEMO_TENANT_ID / tenant desta escola: {tenant_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
