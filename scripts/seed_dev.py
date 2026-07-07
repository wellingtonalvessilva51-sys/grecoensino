"""Seed de desenvolvimento: tenants demo + catálogo de papéis + admin por tenant.

Requer PostgreSQL acessível.

Uso:
    venv\\Scripts\\python.exe -m scripts.seed_dev
"""

from src.core.database import SessionLocal
from src.core.tenancy import reset_current_tenant, set_current_tenant
from src.modules.academico import service as academico
from src.modules.identidade import service as identidade
from src.modules.identidade.schemas import UsuarioCreate
from src.modules.tenancy import service as tenancy
from src.modules.tenancy.schemas import TenantCreate

DEMOS = [
    TenantCreate(nome="Escola A", subdominio="escola-a"),
    TenantCreate(nome="Escola B", subdominio="escola-b"),
]
SENHA_ADMIN = "admin12345"


def main() -> None:
    with SessionLocal() as db:
        identidade.garantir_papeis_catalogo(db)

        for dados in DEMOS:
            tenant = tenancy.buscar_por_subdominio(db, dados.subdominio)
            if tenant is None:
                tenant = tenancy.criar_tenant(db, dados)
                print(f"tenant criado:  {tenant.subdominio} ({tenant.id})")
            else:
                print(f"tenant existe:  {tenant.subdominio} ({tenant.id})")

            email = f"admin@{dados.subdominio}.dev"
            token = set_current_tenant(tenant.id)
            try:
                config = academico.obter_ou_criar_config(db)
                print(
                    f"  config acadêmica: média mín {config.media_minima} / "
                    f"freq mín {config.frequencia_minima_percentual}%"
                )

                if identidade.buscar_usuario_por_email(db, email) is not None:
                    print(f"  admin existe: {email}")
                    continue
                usuario = identidade.criar_usuario(
                    db,
                    UsuarioCreate(
                        nome="Admin",
                        email=email,
                        senha=SENHA_ADMIN,
                        papeis=["admin_tenant"],
                    ),
                )
                print(f"  admin criado: {email} / {SENHA_ADMIN} ({usuario.id})")
            finally:
                reset_current_tenant(token)


if __name__ == "__main__":
    main()
