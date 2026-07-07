"""Reforço de isolamento por tenant na camada de dados (CLAUDE.md §7).

Não se confia no filtro escrito à mão em cada endpoint: estes listeners globais
da Session garantem que TODA leitura/escrita de entidade com `TenantMixin`
respeite o tenant do contexto — falhando fechado quando não há tenant.

Basta importar este módulo para registrar os listeners (feito em database.py).
"""

from sqlalchemy import event
from sqlalchemy.orm import ORMExecuteState, Session, with_loader_criteria

from src.core.exceptions import AppError
from src.core.tenancy import get_current_tenant, require_current_tenant
from src.shared.models import TenantMixin


def _envolve_tenant(execute_state: ORMExecuteState) -> bool:
    return any(
        mapper.class_ is not None and issubclass(mapper.class_, TenantMixin)
        for mapper in execute_state.all_mappers
    )


@event.listens_for(Session, "do_orm_execute")
def _filtrar_por_tenant(execute_state: ORMExecuteState) -> None:
    """Injeta `tenant_id == tenant_atual` em todo SELECT sobre entidade tenant-scoped."""
    if not execute_state.is_select:
        return
    if execute_state.is_column_load or execute_state.is_relationship_load:
        return
    if not _envolve_tenant(execute_state):
        return

    # Fail-closed: sem tenant no contexto, uma consulta tenant-scoped levanta.
    tenant_id = require_current_tenant()

    # tenant_id é variável de fechamento → o lambda-caching do SQLAlchemy o trata
    # como bind param e substitui o valor correto a cada execução (sem vazamento).
    execute_state.statement = execute_state.statement.options(
        with_loader_criteria(
            TenantMixin,
            lambda cls: cls.tenant_id == tenant_id,
            include_aliases=True,
        )
    )


@event.listens_for(Session, "before_flush")
def _carimbar_e_validar_tenant(session: Session, flush_context, instances) -> None:
    """Carimba tenant_id em inserts e bloqueia gravação cruzada entre tenants."""
    atual = get_current_tenant()

    for obj in session.new:
        if not isinstance(obj, TenantMixin):
            continue
        if getattr(obj, "tenant_id", None) is None:
            obj.tenant_id = require_current_tenant()
        elif atual is not None and obj.tenant_id != atual:
            raise AppError(
                codigo="tenant_violacao",
                mensagem="Tentativa de gravar recurso em outro tenant.",
                status_code=403,
            )

    for obj in session.dirty:
        if not isinstance(obj, TenantMixin):
            continue
        if atual is not None and getattr(obj, "tenant_id", None) != atual:
            raise AppError(
                codigo="tenant_violacao",
                mensagem="Tentativa de mover recurso entre tenants.",
                status_code=403,
            )
