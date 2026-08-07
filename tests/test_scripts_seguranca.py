"""Testes das guardas de segurança dos scripts de deploy.

O risco coberto aqui é concreto: o CMD antigo do container rodava o seed demo a
cada boot, recriando `admin@escola-a.dev` com senha conhecida numa base que já
podia ter dado real.
"""

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import src.core.tenant_guard  # noqa: F401  (registra o guard)
from scripts import bootstrap_prod, seed_dev
from src.core.config import settings
from src.core.tenancy import reset_current_tenant, set_current_tenant
from src.modules.identidade import service as identidade
from src.modules.identidade.models import Sessao
from src.modules.identidade.schemas import UsuarioCreate
from src.modules.tenancy.models import Tenant
from src.shared.models import Base


@pytest.fixture()
def db_com_usuario():
    """Sessão SQLite em memória com um tenant e um usuário de senha conhecida."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, future=True)

    with Session() as db:
        identidade.garantir_papeis_catalogo(db)
        tenant = Tenant(nome="Escola A", subdominio="escola-a")
        db.add(tenant)
        db.commit()

        token = set_current_tenant(tenant.id)
        try:
            usuario = identidade.criar_usuario(
                db,
                UsuarioCreate(
                    nome="Admin",
                    email="admin@escola-a.dev",
                    senha="admin12345",
                    papeis=["admin_tenant"],
                ),
            )
            yield db, usuario
        finally:
            reset_current_tenant(token)


# --- seed demo --------------------------------------------------------------
def test_seed_aborta_quando_ambiente_nao_permite(monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "allow_demo_seed", None)

    with pytest.raises(SystemExit, match="ABORTADO"):
        seed_dev.guarda_ambiente()


def test_seed_roda_em_development(monkeypatch):
    monkeypatch.setattr(settings, "environment", "development")
    monkeypatch.setattr(settings, "allow_demo_seed", None)

    seed_dev.guarda_ambiente()  # não levanta


def test_seed_roda_em_producao_com_flag_explicita(monkeypatch):
    # Deploy de vitrine: quem liga a flag assume as senhas conhecidas.
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "allow_demo_seed", True)

    seed_dev.guarda_ambiente()  # não levanta


def test_senhas_demo_podem_vir_do_ambiente():
    # Lidas na importação do módulo; o contrato é o nome da variável.
    assert seed_dev.SENHA_ADMIN
    assert seed_dev.SENHA_RESP
    assert seed_dev.SENHA_SEC
    assert seed_dev.SENHA_PROF


# --- bootstrap de produção --------------------------------------------------
def test_bootstrap_gera_senha_forte_quando_nao_informada(monkeypatch):
    monkeypatch.delenv("BOOTSTRAP_ADMIN_SENHA", raising=False)

    senha, gerada = bootstrap_prod.resolver_senha()

    assert gerada is True
    assert len(senha) >= bootstrap_prod.SENHA_TAMANHO_MINIMO


def test_bootstrap_recusa_senha_curta(monkeypatch):
    monkeypatch.setenv("BOOTSTRAP_ADMIN_SENHA", "123456")

    with pytest.raises(SystemExit, match="muito curta"):
        bootstrap_prod.resolver_senha()


def test_bootstrap_aceita_senha_informada(monkeypatch):
    monkeypatch.setenv("BOOTSTRAP_ADMIN_SENHA", "senha-longa-de-producao")

    senha, gerada = bootstrap_prod.resolver_senha()

    assert (senha, gerada) == ("senha-longa-de-producao", False)


def test_bootstrap_exige_escola_e_admin(monkeypatch):
    for var in ("BOOTSTRAP_ESCOLA", "BOOTSTRAP_SUBDOMINIO", "BOOTSTRAP_ADMIN_EMAIL"):
        monkeypatch.delenv(var, raising=False)

    with pytest.raises(SystemExit):
        bootstrap_prod._argumentos([])


def test_bootstrap_le_parametros_do_ambiente(monkeypatch):
    monkeypatch.setenv("BOOTSTRAP_ESCOLA", "Colégio Exemplo")
    monkeypatch.setenv("BOOTSTRAP_SUBDOMINIO", "colegio-exemplo")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_EMAIL", "diretoria@exemplo.com.br")

    args = bootstrap_prod._argumentos([])

    assert args.escola == "Colégio Exemplo"
    assert args.subdominio == "colegio-exemplo"
    assert args.admin_email == "diretoria@exemplo.com.br"
    assert args.admin_nome == "Administrador"


# --- rotação de senha -------------------------------------------------------
def test_definir_senha_troca_e_revoga_sessoes(db_com_usuario):
    db, usuario = db_com_usuario
    identidade.criar_sessao(db, usuario.id)

    identidade.definir_senha(db, usuario, "senha-nova-forte-2026")

    assert identidade.autenticar(db, usuario.email, "senha-nova-forte-2026") is not None
    assert identidade.autenticar(db, usuario.email, "admin12345") is None
    abertas = db.scalars(
        select(Sessao).where(Sessao.usuario_id == usuario.id, Sessao.revogada_em.is_(None))
    ).all()
    assert abertas == []


def test_sincronizar_senha_ignora_quando_nao_veio_do_ambiente(db_com_usuario):
    # Sem SEED_SENHA_*, o seed nunca deve reescrever a senha de quem já existe.
    db, usuario = db_com_usuario

    seed_dev.sincronizar_senha(db, usuario, "default-fraco", do_env=False)

    assert identidade.autenticar(db, usuario.email, "admin12345") is not None


def test_sincronizar_senha_aplica_senha_do_ambiente(db_com_usuario):
    # Este é o caminho que fecha o buraco numa base já semeada: o usuário demo
    # existe e a senha fraca precisa ser substituída.
    db, usuario = db_com_usuario

    seed_dev.sincronizar_senha(db, usuario, "vitrine-forte-2026", do_env=True)

    assert identidade.autenticar(db, usuario.email, "vitrine-forte-2026") is not None
    assert identidade.autenticar(db, usuario.email, "admin12345") is None


def test_senha_do_env_marca_origem(monkeypatch):
    monkeypatch.delenv("SEED_SENHA_ADMIN", raising=False)
    assert seed_dev._senha("ADMIN", "fraca") == ("fraca", False)

    monkeypatch.setenv("SEED_SENHA_ADMIN", "forte-do-ambiente")
    assert seed_dev._senha("ADMIN", "fraca") == ("forte-do-ambiente", True)


def test_bootstrap_linha_de_comando_vence_ambiente(monkeypatch):
    monkeypatch.setenv("BOOTSTRAP_ESCOLA", "Do ambiente")
    monkeypatch.setenv("BOOTSTRAP_SUBDOMINIO", "amb")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_EMAIL", "amb@exemplo.com")

    args = bootstrap_prod._argumentos(
        ["--escola", "Da linha", "--subdominio", "linha", "--admin-email", "cli@exemplo.com"]
    )

    assert (args.escola, args.subdominio, args.admin_email) == (
        "Da linha",
        "linha",
        "cli@exemplo.com",
    )
