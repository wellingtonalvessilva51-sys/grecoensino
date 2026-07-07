"""Testes de Pagamento (parcial): status pendente/parcial/liquidado, saldo, ACL e auditoria."""

import uuid
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import src.core.tenant_guard  # noqa: F401
from src.core import audit
from src.core.database import get_db
from src.core.security import criar_access_token
from src.core.tenancy import reset_current_tenant, set_current_tenant
from src.main import app
from src.modules.financeiro import service as financeiro
from src.modules.financeiro.schemas import TituloCreate, TituloItemCreate
from src.modules.identidade import service as identidade
from src.modules.identidade.schemas import UsuarioCreate
from src.modules.pessoas import service as pessoas
from src.modules.pessoas.schemas import PessoaCreate, VinculoCreate
from src.modules.tenancy.models import Tenant
from src.shared.deps import Principal
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
        ta = Tenant(nome="Escola A", subdominio="escola-a")
        db.add(ta)
        db.commit()
        id_a = ta.id

        tok = set_current_tenant(id_a)
        try:
            u_fin = identidade.criar_usuario(db, UsuarioCreate(nome="Fin", email="fin@a.dev", senha="senha1234", papeis=["financeiro"]))
            u_resp = identidade.criar_usuario(db, UsuarioCreate(nome="Resp", email="resp@a.dev", senha="senha1234", papeis=["responsavel"]))

            p_resp = pessoas.criar_pessoa(db, PessoaCreate(nome="Responsável", usuario_id=u_resp.id))
            p_dep = pessoas.criar_pessoa(db, PessoaCreate(nome="Aluno Dependente"))
            p_outro = pessoas.criar_pessoa(db, PessoaCreate(nome="Aluno Outro"))
            pessoas.criar_vinculo(db, VinculoCreate(responsavel_id=p_resp.id, aluno_id=p_dep.id))

            # Título de R$ 300,00 para o dependente (item único).
            principal_fin = Principal(usuario=u_fin, papeis=["financeiro"])
            titulo = financeiro.criar_titulo(
                db,
                principal_fin,
                TituloCreate(
                    aluno_id=p_dep.id,
                    competencia="2026-03",
                    vencimento="2026-03-10",
                    itens=[TituloItemCreate(descricao="MENSALIDADE", valor=300)],
                ),
            )
            # Título de outro aluno (para ACL negativa).
            titulo_outro = financeiro.criar_titulo(
                db,
                principal_fin,
                TituloCreate(
                    aluno_id=p_outro.id,
                    competencia="2026-03",
                    vencimento="2026-03-10",
                    itens=[TituloItemCreate(descricao="MENSALIDADE", valor=300)],
                ),
            )
            titulo_id = titulo.id
            titulo_outro_id = titulo_outro.id
        finally:
            reset_current_tenant(tok)

    env = SimpleNamespace(
        Session=Session,
        client=TestClient(app),
        id_a=id_a,
        u_fin_id=u_fin.id,
        tok_fin=criar_access_token(usuario_id=u_fin.id, tenant_id=id_a, papeis=["financeiro"]),
        tok_resp=criar_access_token(usuario_id=u_resp.id, tenant_id=id_a, papeis=["responsavel"]),
        titulo_id=titulo_id,
        titulo_outro_id=titulo_outro_id,
    )
    try:
        yield env
    finally:
        app.dependency_overrides.clear()


def _h(env, token):
    return {"X-Tenant-ID": str(env.id_a), "Authorization": f"Bearer {token}"}


def _pagar(env, token, titulo_id, valor):
    return env.client.post(
        f"/v1/financeiro/titulos/{titulo_id}/pagamentos",
        json={"valor": valor, "data_pagamento": "2026-03-05"},
        headers=_h(env, token),
    )


def _titulo(env, token, titulo_id):
    return env.client.get(f"/v1/financeiro/titulos/{titulo_id}", headers=_h(env, token)).json()


def test_pagamento_parcial(ambiente):
    r = _pagar(ambiente, ambiente.tok_fin, ambiente.titulo_id, 100)
    assert r.status_code == 201
    t = _titulo(ambiente, ambiente.tok_fin, ambiente.titulo_id)
    assert t["status"] == "parcial"
    assert float(t["total_pago"]) == 100.0
    assert float(t["saldo"]) == 200.0


def test_quita_em_dois_pagamentos(ambiente):
    _pagar(ambiente, ambiente.tok_fin, ambiente.titulo_id, 100)
    _pagar(ambiente, ambiente.tok_fin, ambiente.titulo_id, 200)
    t = _titulo(ambiente, ambiente.tok_fin, ambiente.titulo_id)
    assert t["status"] == "liquidado"
    assert float(t["total_pago"]) == 300.0
    assert float(t["saldo"]) == 0.0


def test_pagamento_unico_total_liquida(ambiente):
    r = _pagar(ambiente, ambiente.tok_fin, ambiente.titulo_id, 300)
    assert r.status_code == 201
    t = _titulo(ambiente, ambiente.tok_fin, ambiente.titulo_id)
    assert t["status"] == "liquidado"


def test_pagamento_excede_saldo_400(ambiente):
    r = _pagar(ambiente, ambiente.tok_fin, ambiente.titulo_id, 400)
    assert r.status_code == 400
    assert r.json()["erro"]["codigo"] == "pagamento_excede_saldo"


def test_pagamento_excede_saldo_apos_parcial_400(ambiente):
    _pagar(ambiente, ambiente.tok_fin, ambiente.titulo_id, 250)
    r = _pagar(ambiente, ambiente.tok_fin, ambiente.titulo_id, 100)  # saldo 50
    assert r.status_code == 400


def test_responsavel_nao_registra_pagamento_403(ambiente):
    r = _pagar(ambiente, ambiente.tok_resp, ambiente.titulo_id, 100)
    assert r.status_code == 403


def test_pagamento_titulo_inexistente_404(ambiente):
    r = _pagar(ambiente, ambiente.tok_fin, uuid.uuid4(), 100)
    assert r.status_code == 404
    assert r.json()["erro"]["codigo"] == "titulo_nao_encontrado"


def test_responsavel_ve_pagamentos_do_dependente(ambiente):
    _pagar(ambiente, ambiente.tok_fin, ambiente.titulo_id, 100)
    r = ambiente.client.get(
        f"/v1/financeiro/titulos/{ambiente.titulo_id}/pagamentos",
        headers=_h(ambiente, ambiente.tok_resp),
    )
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_responsavel_nao_ve_pagamentos_de_outro_404(ambiente):
    r = ambiente.client.get(
        f"/v1/financeiro/titulos/{ambiente.titulo_outro_id}/pagamentos",
        headers=_h(ambiente, ambiente.tok_resp),
    )
    assert r.status_code == 404


def test_filtro_titulos_por_status_apos_pagamento(ambiente):
    _pagar(ambiente, ambiente.tok_fin, ambiente.titulo_id, 300)  # liquida
    r = ambiente.client.get("/v1/financeiro/titulos?status=liquidado", headers=_h(ambiente, ambiente.tok_fin))
    ids = {t["id"] for t in r.json()}
    assert str(ambiente.titulo_id) in ids
    assert str(ambiente.titulo_outro_id) not in ids  # esse segue pendente


def test_auditoria_registra_pagamento(ambiente):
    _pagar(ambiente, ambiente.tok_fin, ambiente.titulo_id, 120)
    tok = set_current_tenant(ambiente.id_a)
    try:
        with ambiente.Session() as db:
            trilha = audit.listar(db, entidade="pagamento")
    finally:
        reset_current_tenant(tok)
    assert len(trilha) == 1
    assert trilha[0].acao == "pagar"
    assert trilha[0].usuario_id == ambiente.u_fin_id
    assert trilha[0].dados_depois["valor"] == 120.0
    assert trilha[0].dados_depois["status"] == "parcial"
