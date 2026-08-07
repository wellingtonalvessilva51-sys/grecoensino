"""Testes das guardas de segurança dos scripts de deploy.

O risco coberto aqui é concreto: o CMD antigo do container rodava o seed demo a
cada boot, recriando `admin@escola-a.dev` com senha conhecida numa base que já
podia ter dado real.
"""

import pytest

from scripts import bootstrap_prod, seed_dev
from src.core.config import settings


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
