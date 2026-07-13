"""Seed de desenvolvimento: tenants demo + papéis + admin + cenário do Portal.

Requer PostgreSQL acessível. Idempotente (pode rodar várias vezes).

Uso:
    venv\\Scripts\\python.exe -m scripts.seed_dev
"""

from datetime import date, timedelta

from sqlalchemy import select

from src.core.database import SessionLocal
from src.core.tenancy import reset_current_tenant, set_current_tenant
from src.modules.academico import service as academico
from src.modules.academico.schemas import (
    AnoLetivoCreate,
    AtribuicaoCreate,
    CursoCreate,
    DisciplinaCreate,
    FrequenciaCreate,
    MatriculaCreate,
    NotaCreate,
    SerieCreate,
    TurmaCreate,
)
from src.modules.comunicacao import service as comunicacao
from src.modules.comunicacao.schemas import RecadoCreate
from src.modules.financeiro import service as financeiro
from src.modules.financeiro.schemas import (
    PagamentoCreate,
    TituloCreate,
    TituloItemCreate,
)
from src.modules.identidade import service as identidade
from src.modules.identidade.schemas import UsuarioCreate
from src.modules.pessoas import service as pessoas
from src.modules.pessoas.models import Pessoa
from src.modules.pessoas.schemas import PessoaCreate, VinculoCreate
from src.modules.tenancy import service as tenancy
from src.modules.tenancy.schemas import TenantCreate
from src.shared.deps import Principal

DEMOS = [
    TenantCreate(nome="Escola A", subdominio="escola-a"),
    TenantCreate(nome="Escola B", subdominio="escola-b"),
]
SENHA_ADMIN = "admin12345"
SENHA_RESP = "resp12345"
SENHA_SEC = "sec12345"
SENHA_PROF = "prof12345"


def _garantir_secretaria(db) -> None:
    email = "secretaria@escola-a.dev"
    if identidade.buscar_usuario_por_email(db, email) is not None:
        print(f"  secretaria existe: {email}")
        return
    identidade.criar_usuario(
        db,
        UsuarioCreate(nome="Sônia (Secretaria)", email=email, senha=SENHA_SEC, papeis=["secretaria"]),
    )
    print(f"  secretaria criada: {email} / {SENHA_SEC}")


def _garantir_admin(db, subdominio: str):
    email = f"admin@{subdominio}.dev"
    usuario = identidade.buscar_usuario_por_email(db, email)
    if usuario is not None:
        print(f"  admin existe: {email}")
        return usuario
    usuario = identidade.criar_usuario(
        db,
        UsuarioCreate(nome="Admin", email=email, senha=SENHA_ADMIN, papeis=["admin_tenant"]),
    )
    print(f"  admin criado: {email} / {SENHA_ADMIN}")
    return usuario


def _garantir_professor_demo(db) -> None:
    """Garante o usuário professor e o liga à pessoa 'Prof. Ana Lima' (para bases
    já semeadas antes do login de professor existir)."""
    email = "professor@escola-a.dev"
    usuario = identidade.buscar_usuario_por_email(db, email)
    if usuario is None:
        usuario = identidade.criar_usuario(
            db,
            UsuarioCreate(nome="Ana Lima", email=email, senha=SENHA_PROF, papeis=["professor"]),
        )
        print(f"  professor criado: {email} / {SENHA_PROF}")
    else:
        print(f"  professor existe: {email}")

    pessoa = db.scalars(
        select(Pessoa).where(Pessoa.nome == "Prof. Ana Lima", Pessoa.deleted_at.is_(None))
    ).first()
    if pessoa is not None and pessoa.usuario_id is None:
        pessoa.usuario_id = usuario.id
        db.commit()
        print("  professor vinculado à pessoa 'Prof. Ana Lima'")


def _seed_portal(db, admin) -> None:
    """Cria um cenário do Portal do Responsável (responsável + aluno + dados)."""
    resp_email = "responsavel@escola-a.dev"
    if identidade.buscar_usuario_por_email(db, resp_email) is not None:
        print(f"  cenário do portal já existe (login {resp_email} / {SENHA_RESP})")
        return

    principal = Principal(usuario=admin, papeis=["admin_tenant"])

    # Responsável (com login) + aluno dependente + professor.
    u_resp = identidade.criar_usuario(
        db,
        UsuarioCreate(nome="Maria Souza", email=resp_email, senha=SENHA_RESP, papeis=["responsavel"]),
    )
    u_prof = identidade.criar_usuario(
        db,
        UsuarioCreate(nome="Ana Lima", email="professor@escola-a.dev", senha=SENHA_PROF, papeis=["professor"]),
    )
    p_resp = pessoas.criar_pessoa(db, PessoaCreate(nome="Maria Souza", usuario_id=u_resp.id))
    p_aluno = pessoas.criar_pessoa(db, PessoaCreate(nome="João Souza"))
    p_prof = pessoas.criar_pessoa(db, PessoaCreate(nome="Prof. Ana Lima", usuario_id=u_prof.id))
    pessoas.criar_vinculo(
        db, VinculoCreate(responsavel_id=p_resp.id, aluno_id=p_aluno.id, financeiro=True)
    )

    # Estrutura acadêmica + matrícula.
    ano = academico.criar_ano_letivo(db, AnoLetivoCreate(ano=2026))
    curso = academico.criar_curso(db, CursoCreate(nome="Ensino Fundamental"))
    serie = academico.criar_serie(db, SerieCreate(curso_id=curso.id, nome="5º ano", ordem=5))
    disc = academico.criar_disciplina(db, DisciplinaCreate(nome="Matemática"))
    turma = academico.criar_turma(
        db, TurmaCreate(serie_id=serie.id, ano_letivo_id=ano.id, nome="A")
    )
    academico.atribuir_disciplina(
        db, turma.id, AtribuicaoCreate(disciplina_id=disc.id, professor_id=p_prof.id)
    )
    matricula = academico.criar_matricula(
        db, MatriculaCreate(aluno_id=p_aluno.id, turma_id=turma.id)
    )

    # Notas (4 períodos) → boletim.
    for periodo, valor in enumerate([7.5, 8.0, 6.0, 9.0], start=1):
        academico.registrar_nota(
            db,
            principal,
            NotaCreate(
                matricula_id=matricula.id, disciplina_id=disc.id, periodo=periodo, valor=valor
            ),
        )

    # Frequência: 20 dias letivos, 18 presenças (90%).
    inicio = date(2026, 3, 2)
    for i in range(20):
        academico.registrar_frequencia(
            db,
            principal,
            FrequenciaCreate(
                matricula_id=matricula.id, data=inicio + timedelta(days=i), presente=i < 18
            ),
        )

    # Financeiro: título consolidado (mensalidade + material) com pagamento parcial.
    titulo = financeiro.criar_titulo(
        db,
        principal,
        TituloCreate(
            aluno_id=p_aluno.id,
            competencia="2026-03",
            vencimento=date(2026, 3, 10),
            descricao="Mensalidade de março",
            itens=[
                TituloItemCreate(descricao="MENSALIDADE", valor=500),
                TituloItemCreate(descricao="MATERIAL", valor=150),
            ],
        ),
    )
    financeiro.registrar_pagamento(
        db, principal, titulo.id, PagamentoCreate(valor=300, data_pagamento=date(2026, 3, 8))
    )

    # Recado institucional para o aluno e o responsável.
    comunicacao.criar_recado(
        db,
        principal,
        RecadoCreate(
            titulo="Reunião de pais",
            mensagem="A reunião de pais será no dia 20/03 às 19h no auditório.",
            destinatarios=[p_aluno.id, p_resp.id],
        ),
    )

    print(f"  cenário do portal criado: login {resp_email} / {SENHA_RESP}")
    print(f"  professor criado: professor@escola-a.dev / {SENHA_PROF}")


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

            token = set_current_tenant(tenant.id)
            try:
                academico.obter_ou_criar_config(db)
                admin = _garantir_admin(db, dados.subdominio)
                if dados.subdominio == "escola-a":
                    _garantir_secretaria(db)
                    _seed_portal(db, admin)
                    _garantir_professor_demo(db)
            finally:
                reset_current_tenant(token)


if __name__ == "__main__":
    main()
