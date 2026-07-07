"""Testes de Pessoas: RBAC de escrita, ACL de leitura e isolamento por tenant."""

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import src.core.tenant_guard  # noqa: F401
from src.core.database import get_db
from src.core.security import criar_access_token
from src.core.tenancy import reset_current_tenant, set_current_tenant
from src.main import app
from src.modules.identidade import service as identidade
from src.modules.identidade.schemas import UsuarioCreate
from src.modules.pessoas import service as pessoas
from src.modules.pessoas.schemas import PessoaCreate, VinculoCreate
from src.modules.tenancy.models import Tenant
from src.shared.models import Base


@pytest.fixture()
def ambiente():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, future=True, expire_on_commit=False)

    def _get_db_override():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _get_db_override

    with Session() as db:
        identidade.garantir_papeis_catalogo(db)
        tenant_a = Tenant(nome="Escola A", subdominio="escola-a")
        tenant_b = Tenant(nome="Escola B", subdominio="escola-b")
        db.add_all([tenant_a, tenant_b])
        db.commit()
        id_a, id_b = tenant_a.id, tenant_b.id

        tok = set_current_tenant(id_a)
        try:
            u_sec = identidade.criar_usuario(
                db, UsuarioCreate(nome="Sec", email="sec@a.dev", senha="senha1234", papeis=["secretaria"])
            )
            u_resp = identidade.criar_usuario(
                db, UsuarioCreate(nome="Resp", email="resp@a.dev", senha="senha1234", papeis=["responsavel"])
            )
            p_resp = pessoas.criar_pessoa(db, PessoaCreate(nome="Responsável", usuario_id=u_resp.id))
            p_dep = pessoas.criar_pessoa(db, PessoaCreate(nome="Aluno Dependente"))
            p_outro = pessoas.criar_pessoa(db, PessoaCreate(nome="Aluno Outra Família"))
            pessoas.criar_vinculo(
                db, VinculoCreate(responsavel_id=p_resp.id, aluno_id=p_dep.id, financeiro=True)
            )
        finally:
            reset_current_tenant(tok)

        tok_b = set_current_tenant(id_b)
        try:
            p_b = pessoas.criar_pessoa(db, PessoaCreate(nome="Pessoa do Tenant B"))
        finally:
            reset_current_tenant(tok_b)

    dados = SimpleNamespace(
        client=TestClient(app),
        id_a=id_a,
        id_b=id_b,
        tok_sec=criar_access_token(usuario_id=u_sec.id, tenant_id=id_a, papeis=["secretaria"]),
        tok_resp=criar_access_token(usuario_id=u_resp.id, tenant_id=id_a, papeis=["responsavel"]),
        p_resp_id=p_resp.id,
        p_dep_id=p_dep.id,
        p_outro_id=p_outro.id,
        p_b_id=p_b.id,
    )
    try:
        yield dados
    finally:
        app.dependency_overrides.clear()


def _h(env, token):
    return {"X-Tenant-ID": str(env.id_a), "Authorization": f"Bearer {token}"}


def test_secretaria_cria_pessoa(ambiente):
    r = ambiente.client.post(
        "/v1/pessoas",
        json={"nome": "Novo Aluno", "cpf": "123.456.789-09"},
        headers=_h(ambiente, ambiente.tok_sec),
    )
    assert r.status_code == 201
    assert r.json()["cpf"] == "12345678909"  # normalizado a dígitos


def test_responsavel_nao_pode_criar_403(ambiente):
    r = ambiente.client.post(
        "/v1/pessoas",
        json={"nome": "X"},
        headers=_h(ambiente, ambiente.tok_resp),
    )
    assert r.status_code == 403
    assert r.json()["erro"]["codigo"] == "permissao_negada"


def test_responsavel_ve_o_proprio_dependente(ambiente):
    r = ambiente.client.get(
        f"/v1/pessoas/{ambiente.p_dep_id}", headers=_h(ambiente, ambiente.tok_resp)
    )
    assert r.status_code == 200
    assert r.json()["nome"] == "Aluno Dependente"


def test_responsavel_nao_ve_outra_familia_404(ambiente):
    r = ambiente.client.get(
        f"/v1/pessoas/{ambiente.p_outro_id}", headers=_h(ambiente, ambiente.tok_resp)
    )
    assert r.status_code == 404


def test_secretaria_ve_qualquer_pessoa(ambiente):
    r = ambiente.client.get(
        f"/v1/pessoas/{ambiente.p_outro_id}", headers=_h(ambiente, ambiente.tok_sec)
    )
    assert r.status_code == 200


def test_lista_responsavel_so_self_e_dependentes(ambiente):
    r = ambiente.client.get("/v1/pessoas", headers=_h(ambiente, ambiente.tok_resp))
    assert r.status_code == 200
    ids = {p["id"] for p in r.json()}
    assert ids == {str(ambiente.p_resp_id), str(ambiente.p_dep_id)}


def test_contatos_e_enderecos_embutidos(ambiente):
    payload = {
        "nome": "Com Contato",
        "contatos": [{"tipo": "email", "valor": "a@b.dev"}],
        "enderecos": [
            {
                "logradouro": "Rua 1",
                "numero": "10",
                "cidade": "São Paulo",
                "uf": "sp",
                "cep": "01000-000",
            }
        ],
    }
    criado = ambiente.client.post(
        "/v1/pessoas", json=payload, headers=_h(ambiente, ambiente.tok_sec)
    )
    assert criado.status_code == 201
    pid = criado.json()["id"]

    r = ambiente.client.get(f"/v1/pessoas/{pid}", headers=_h(ambiente, ambiente.tok_sec))
    corpo = r.json()
    assert corpo["contatos"][0]["valor"] == "a@b.dev"
    assert corpo["enderecos"][0]["uf"] == "SP"  # normalizado
    assert corpo["enderecos"][0]["cep"] == "01000000"


def test_isolamento_tenant_pessoa_de_b_invisivel_em_a(ambiente):
    # secretaria do tenant A tentando ler pessoa do tenant B → 404 (guard filtra).
    r = ambiente.client.get(
        f"/v1/pessoas/{ambiente.p_b_id}", headers=_h(ambiente, ambiente.tok_sec)
    )
    assert r.status_code == 404
