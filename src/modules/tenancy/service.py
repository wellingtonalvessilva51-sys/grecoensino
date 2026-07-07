"""Serviço do módulo tenancy.

Usado pelo middleware de resolução de tenant, pelo seed de desenvolvimento e
pelos testes. Ainda sem router: a gestão de tenants é do admin_plataforma e
entra com autenticação no passo 3.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.tenancy.models import Tenant
from src.modules.tenancy.schemas import TenantCreate


def criar_tenant(db: Session, dados: TenantCreate) -> Tenant:
    tenant = Tenant(nome=dados.nome, subdominio=dados.subdominio)
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant


def buscar_por_subdominio(db: Session, subdominio: str) -> Tenant | None:
    stmt = select(Tenant).where(
        Tenant.subdominio == subdominio,
        Tenant.ativo.is_(True),
        Tenant.deleted_at.is_(None),
    )
    return db.scalars(stmt).first()


def listar(db: Session) -> list[Tenant]:
    stmt = select(Tenant).where(Tenant.deleted_at.is_(None))
    return list(db.scalars(stmt).all())
