"""Seed de desenvolvimento: cria tenants demo. Requer PostgreSQL acessível.

Uso:
    venv\\Scripts\\python.exe -m scripts.seed_dev
"""

from src.core.database import SessionLocal
from src.modules.tenancy import service
from src.modules.tenancy.schemas import TenantCreate

DEMOS = [
    TenantCreate(nome="Escola A", subdominio="escola-a"),
    TenantCreate(nome="Escola B", subdominio="escola-b"),
]


def main() -> None:
    with SessionLocal() as db:
        for dados in DEMOS:
            existente = service.buscar_por_subdominio(db, dados.subdominio)
            if existente is not None:
                print(f"já existe: {existente.subdominio} ({existente.id})")
                continue
            tenant = service.criar_tenant(db, dados)
            print(f"criado:   {tenant.subdominio} ({tenant.id})")


if __name__ == "__main__":
    main()
