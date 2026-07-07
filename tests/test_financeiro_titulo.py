"""Testes do Título consolidado: soma dos itens, unicidade (§4), RBAC, ACL e auditoria."""

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
        ta = Tenant(nome="Escola A", subdominio="escola-a")
        db.add(ta)
        db.commit()
        id_a = ta.id

        tok = set_current_tenant(id_a)
        try:
            u_sec = identidade.criar_usuario(db, UsuarioCreate(nome="Sec", email="sec@a.dev", senha="senha1234", papeis=["secretaria"]))
            u_fin = identidade.criar_usuario(db, UsuarioCreate(nome="Fin", email="fin@a.dev", senha="senha1234", papeis=["financeiro"]))
            u_resp = identidade.criar_usuario(db, UsuarioCreate(nome="Resp", email="resp@a.dev", senha="senha1234", papeis=["responsavel"]))

            p_resp = pessoas.criar_pessoa(db, PessoaCreate(nome="Responsável", usuario_id=u_resp.id))
            p_dep = pessoas.criar_pessoa(db, PessoaCreate(nome="Aluno Dependente"))
            p_outro = pessoas.criar_pessoa(db, PessoaCreate(nome="Aluno Outro"))
            # Vínculo sem financeiro=True: mesmo assim vê (decisão: qualquer responsável vinculado).
            pessoas.criar_vinculo(db, VinculoCreate(responsavel_id=p_resp.id, aluno_id=p_dep.id))
        finally:
            reset_current_tenant(tok)

    env = SimpleNamespace(
        Session=Session,
        client=TestClient(app),
        id_a=id_a,
        u_sec_id=u_sec.id,
        tok_sec=criar_access_token(usuario_id=u_sec.id, tenant_id=id_a, papeis=["secretaria"]),
        tok_fin=criar_access_token(usuario_id=u_fin.id, tenant_id=id_a, papeis=["financeiro"]),
        tok_resp=criar_access_token(usuario_id=u_resp.id, tenant_id=id_a, papeis=["responsavel"]),
        aluno_dep_id=p_dep.id,
        aluno_outro_id=p_outro.id,
    )
    try:
        yield env
    finally:
        app.dependency_overrides.clear()


def _h(env, token):
    return {"X-Tenant-ID": str(env.id_a), "Authorization": f"Bearer {token}"}


_ITENS_PADRAO = [
    {"descricao": "MENSALIDADE", "valor": 500},
    {"descricao": "VÔLEI", "valor": 80.50},
    {"descricao": "ROBÓTICA", "valor": 120},
]


def _payload(aluno_id, competencia="2026-03", itens=None):
    return {
        "aluno_id": str(aluno_id),
        "competencia": competencia,
        "vencimento": "2026-03-10",
        "descricao": "Mensalidade consolidada",
        # None = usa o padrão; lista vazia é enviada como está (para testar 422).
        "itens": _ITENS_PADRAO if itens is None else itens,
    }


def test_secretaria_cria_titulo_consolidado(ambiente):
    r = ambiente.client.post("/v1/financeiro/titulos", json=_payload(ambiente.aluno_dep_id), headers=_h(ambiente, ambiente.tok_sec))
    assert r.status_code == 201
    body = r.json()
    assert float(body["valor_total"]) == 700.50  # 500 + 80.50 + 120
    assert body["status"] == "pendente"
    assert float(body["total_pago"]) == 0.0
    assert float(body["saldo"]) == 700.50
    assert len(body["itens"]) == 3


def test_financeiro_pode_criar(ambiente):
    r = ambiente.client.post("/v1/financeiro/titulos", json=_payload(ambiente.aluno_dep_id), headers=_h(ambiente, ambiente.tok_fin))
    assert r.status_code == 201


def test_responsavel_nao_cria_403(ambiente):
    r = ambiente.client.post("/v1/financeiro/titulos", json=_payload(ambiente.aluno_dep_id), headers=_h(ambiente, ambiente.tok_resp))
    assert r.status_code == 403


def test_titulo_duplicado_mesma_competencia_409(ambiente):
    ambiente.client.post("/v1/financeiro/titulos", json=_payload(ambiente.aluno_dep_id), headers=_h(ambiente, ambiente.tok_sec))
    r = ambiente.client.post("/v1/financeiro/titulos", json=_payload(ambiente.aluno_dep_id), headers=_h(ambiente, ambiente.tok_sec))
    assert r.status_code == 409
    assert r.json()["erro"]["codigo"] == "titulo_duplicado"


def test_aluno_inexistente_404(ambiente):
    r = ambiente.client.post("/v1/financeiro/titulos", json=_payload(uuid.uuid4()), headers=_h(ambiente, ambiente.tok_sec))
    assert r.status_code == 404
    assert r.json()["erro"]["codigo"] == "aluno_inexistente"


def test_titulo_sem_itens_422(ambiente):
    r = ambiente.client.post("/v1/financeiro/titulos", json=_payload(ambiente.aluno_dep_id, itens=[]), headers=_h(ambiente, ambiente.tok_sec))
    assert r.status_code == 422


def test_competencia_invalida_422(ambiente):
    r = ambiente.client.post("/v1/financeiro/titulos", json=_payload(ambiente.aluno_dep_id, competencia="2026-13"), headers=_h(ambiente, ambiente.tok_sec))
    assert r.status_code == 422


def test_responsavel_ve_titulo_do_dependente(ambiente):
    criado = ambiente.client.post("/v1/financeiro/titulos", json=_payload(ambiente.aluno_dep_id), headers=_h(ambiente, ambiente.tok_sec))
    tid = criado.json()["id"]
    r = ambiente.client.get(f"/v1/financeiro/titulos/{tid}", headers=_h(ambiente, ambiente.tok_resp))
    assert r.status_code == 200


def test_responsavel_nao_ve_titulo_de_outro_404(ambiente):
    criado = ambiente.client.post("/v1/financeiro/titulos", json=_payload(ambiente.aluno_outro_id), headers=_h(ambiente, ambiente.tok_sec))
    tid = criado.json()["id"]
    r = ambiente.client.get(f"/v1/financeiro/titulos/{tid}", headers=_h(ambiente, ambiente.tok_resp))
    assert r.status_code == 404


def test_lista_responsavel_so_do_dependente(ambiente):
    ambiente.client.post("/v1/financeiro/titulos", json=_payload(ambiente.aluno_dep_id), headers=_h(ambiente, ambiente.tok_sec))
    ambiente.client.post("/v1/financeiro/titulos", json=_payload(ambiente.aluno_outro_id), headers=_h(ambiente, ambiente.tok_sec))
    r = ambiente.client.get("/v1/financeiro/titulos", headers=_h(ambiente, ambiente.tok_resp))
    alunos = {t["aluno_id"] for t in r.json()}
    assert alunos == {str(ambiente.aluno_dep_id)}


def test_filtro_por_status(ambiente):
    ambiente.client.post("/v1/financeiro/titulos", json=_payload(ambiente.aluno_dep_id), headers=_h(ambiente, ambiente.tok_sec))
    r = ambiente.client.get("/v1/financeiro/titulos?status=pendente", headers=_h(ambiente, ambiente.tok_sec))
    assert len(r.json()) == 1
    r2 = ambiente.client.get("/v1/financeiro/titulos?status=liquidado", headers=_h(ambiente, ambiente.tok_sec))
    assert r2.json() == []


def test_auditoria_registra_criacao(ambiente):
    ambiente.client.post("/v1/financeiro/titulos", json=_payload(ambiente.aluno_dep_id), headers=_h(ambiente, ambiente.tok_sec))
    tok = set_current_tenant(ambiente.id_a)
    try:
        with ambiente.Session() as db:
            trilha = audit.listar(db, entidade="titulo")
    finally:
        reset_current_tenant(tok)
    assert len(trilha) == 1
    assert trilha[0].acao == "criar"
    assert trilha[0].usuario_id == ambiente.u_sec_id
    assert trilha[0].dados_depois["valor_total"] == 700.50
