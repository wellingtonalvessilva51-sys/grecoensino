"""Serviço do Acadêmico: estrutura curricular, atribuições e matrícula.

Valida referências a pessoas (aluno/professor) chamando `pessoas.service`, sem
importar models de outro módulo (§6). ACL de matrícula reusa
`pessoas.service.ids_visiveis`.
"""

import uuid
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.core.exceptions import AppError
from src.modules.academico.models import (
    AnoLetivo,
    ConfigAcademica,
    Curso,
    Disciplina,
    Frequencia,
    Matricula,
    Serie,
    Turma,
    TurmaDisciplinaProfessor,
)
from src.modules.academico.schemas import (
    AnoLetivoCreate,
    AtribuicaoCreate,
    ConfigAcademicaUpdate,
    CursoCreate,
    DisciplinaCreate,
    FrequenciaCreate,
    FrequenciaResumo,
    MatriculaCreate,
    SerieCreate,
    TurmaCreate,
)
from src.modules.pessoas import service as pessoas

# Papéis que lançam frequência/nota em qualquer turma do tenant (sem ACL de docência).
PAPEIS_LANCA_PRIVILEGIADO = {"secretaria", "admin_tenant", "admin_plataforma"}

# Defaults sensatos: toda escola nova já nasce com regra definida (§4).
CONFIG_DEFAULTS = {
    "media_minima": 6.00,
    "num_periodos": 4,
    "pesos_periodos": [1, 1, 1, 1],
    "frequencia_minima_percentual": 75.00,
}


def _ativos(model):
    return select(model).where(model.deleted_at.is_(None))


def _obter(db: Session, model, id_: uuid.UUID):
    return db.scalars(_ativos(model).where(model.id == id_)).first()


# --- Configuração acadêmica (regras por escola) -----------------------------
def obter_ou_criar_config(db: Session) -> ConfigAcademica:
    """Config do tenant atual; cria com defaults na primeira vez (§4)."""
    config = db.scalars(_ativos(ConfigAcademica)).first()
    if config is None:
        config = ConfigAcademica(**CONFIG_DEFAULTS)
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


def atualizar_config(db: Session, dados: ConfigAcademicaUpdate) -> ConfigAcademica:
    config = obter_ou_criar_config(db)
    config.media_minima = dados.media_minima
    config.num_periodos = dados.num_periodos
    config.pesos_periodos = [float(p) for p in dados.pesos_periodos]
    config.frequencia_minima_percentual = dados.frequencia_minima_percentual
    db.commit()
    db.refresh(config)
    return config


# --- Ano letivo -------------------------------------------------------------
def criar_ano_letivo(db: Session, dados: AnoLetivoCreate) -> AnoLetivo:
    obj = AnoLetivo(ano=dados.ano, descricao=dados.descricao, situacao=dados.situacao)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def listar_anos_letivos(db: Session) -> list[AnoLetivo]:
    return list(db.scalars(_ativos(AnoLetivo).order_by(AnoLetivo.ano.desc())).all())


# --- Curso ------------------------------------------------------------------
def criar_curso(db: Session, dados: CursoCreate) -> Curso:
    obj = Curso(nome=dados.nome, codigo=dados.codigo)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def listar_cursos(db: Session) -> list[Curso]:
    return list(db.scalars(_ativos(Curso).order_by(Curso.nome)).all())


# --- Série ------------------------------------------------------------------
def criar_serie(db: Session, dados: SerieCreate) -> Serie:
    if _obter(db, Curso, dados.curso_id) is None:
        raise AppError("curso_inexistente", "Curso não encontrado.", status_code=404)
    obj = Serie(curso_id=dados.curso_id, nome=dados.nome, ordem=dados.ordem)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def listar_series(db: Session, curso_id: uuid.UUID | None = None) -> list[Serie]:
    stmt = _ativos(Serie)
    if curso_id is not None:
        stmt = stmt.where(Serie.curso_id == curso_id)
    return list(db.scalars(stmt.order_by(Serie.ordem)).all())


# --- Disciplina -------------------------------------------------------------
def criar_disciplina(db: Session, dados: DisciplinaCreate) -> Disciplina:
    obj = Disciplina(nome=dados.nome, codigo=dados.codigo)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def listar_disciplinas(db: Session) -> list[Disciplina]:
    return list(db.scalars(_ativos(Disciplina).order_by(Disciplina.nome)).all())


# --- Turma ------------------------------------------------------------------
def criar_turma(db: Session, dados: TurmaCreate) -> Turma:
    if _obter(db, Serie, dados.serie_id) is None:
        raise AppError("serie_inexistente", "Série não encontrada.", status_code=404)
    if _obter(db, AnoLetivo, dados.ano_letivo_id) is None:
        raise AppError("ano_letivo_inexistente", "Ano letivo não encontrado.", status_code=404)
    obj = Turma(
        serie_id=dados.serie_id, ano_letivo_id=dados.ano_letivo_id, nome=dados.nome
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def obter_turma(db: Session, turma_id: uuid.UUID) -> Turma | None:
    return _obter(db, Turma, turma_id)


def listar_turmas(db: Session) -> list[Turma]:
    return list(db.scalars(_ativos(Turma).order_by(Turma.nome)).all())


# --- Atribuição disciplina/professor (TDP) ----------------------------------
def atribuir_disciplina(
    db: Session, turma_id: uuid.UUID, dados: AtribuicaoCreate
) -> TurmaDisciplinaProfessor:
    if _obter(db, Turma, turma_id) is None:
        raise AppError("turma_inexistente", "Turma não encontrada.", status_code=404)
    if _obter(db, Disciplina, dados.disciplina_id) is None:
        raise AppError("disciplina_inexistente", "Disciplina não encontrada.", status_code=404)
    if pessoas.obter_pessoa(db, dados.professor_id) is None:
        raise AppError("professor_inexistente", "Professor não encontrado.", status_code=404)

    obj = TurmaDisciplinaProfessor(
        turma_id=turma_id,
        disciplina_id=dados.disciplina_id,
        professor_id=dados.professor_id,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def listar_atribuicoes(db: Session, turma_id: uuid.UUID) -> list[TurmaDisciplinaProfessor]:
    stmt = _ativos(TurmaDisciplinaProfessor).where(
        TurmaDisciplinaProfessor.turma_id == turma_id
    )
    return list(db.scalars(stmt).all())


# --- Matrícula --------------------------------------------------------------
def criar_matricula(db: Session, dados: MatriculaCreate) -> Matricula:
    if _obter(db, Turma, dados.turma_id) is None:
        raise AppError("turma_inexistente", "Turma não encontrada.", status_code=404)
    if pessoas.obter_pessoa(db, dados.aluno_id) is None:
        raise AppError("aluno_inexistente", "Aluno não encontrado.", status_code=404)

    existente = db.scalars(
        _ativos(Matricula).where(
            Matricula.aluno_id == dados.aluno_id,
            Matricula.turma_id == dados.turma_id,
        )
    ).first()
    if existente is not None:
        raise AppError(
            "matricula_duplicada", "Aluno já matriculado nesta turma.", status_code=409
        )

    obj = Matricula(
        aluno_id=dados.aluno_id,
        turma_id=dados.turma_id,
        situacao=dados.situacao,
        data_matricula=dados.data_matricula or date.today(),
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def obter_matricula(db: Session, matricula_id: uuid.UUID) -> Matricula | None:
    return _obter(db, Matricula, matricula_id)


def listar_matriculas(db: Session, principal) -> list[Matricula]:
    ids = pessoas.ids_visiveis(db, principal)  # None = privilegiado (vê todas)
    stmt = _ativos(Matricula)
    if ids is not None:
        if not ids:
            return []
        stmt = stmt.where(Matricula.aluno_id.in_(ids))
    return list(db.scalars(stmt).all())


def pode_ver_matricula(db: Session, principal, matricula: Matricula) -> bool:
    ids = pessoas.ids_visiveis(db, principal)
    return ids is None or matricula.aluno_id in ids


# --- Frequência (diária, por dia letivo) ------------------------------------
def professor_leciona_turma(db: Session, principal, turma_id: uuid.UUID) -> bool:
    """True se o principal pode lançar na turma: privilegiado ou professor dela."""
    if PAPEIS_LANCA_PRIVILEGIADO.intersection(principal.papeis):
        return True
    minha = pessoas.pessoa_do_usuario(db, principal.usuario.id)
    if minha is None:
        return False
    vinculo = db.scalars(
        _ativos(TurmaDisciplinaProfessor).where(
            TurmaDisciplinaProfessor.turma_id == turma_id,
            TurmaDisciplinaProfessor.professor_id == minha.id,
        )
    ).first()
    return vinculo is not None


def registrar_frequencia(db: Session, principal, dados: FrequenciaCreate) -> Frequencia:
    matricula = _obter(db, Matricula, dados.matricula_id)
    if matricula is None:
        raise AppError("matricula_inexistente", "Matrícula não encontrada.", status_code=404)
    if not professor_leciona_turma(db, principal, matricula.turma_id):
        raise AppError(
            "sem_permissao_turma",
            "Professor não leciona nesta turma.",
            status_code=403,
        )

    # Upsert por (matrícula, data): relançar o dia atualiza o registro.
    existente = db.scalars(
        _ativos(Frequencia).where(
            Frequencia.matricula_id == dados.matricula_id,
            Frequencia.data == dados.data,
        )
    ).first()
    justificada = dados.justificada and not dados.presente
    if existente is not None:
        existente.presente = dados.presente
        existente.justificada = justificada
        db.commit()
        db.refresh(existente)
        return existente

    obj = Frequencia(
        matricula_id=dados.matricula_id,
        data=dados.data,
        presente=dados.presente,
        justificada=justificada,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def listar_frequencias(db: Session, matricula_id: uuid.UUID) -> list[Frequencia]:
    stmt = _ativos(Frequencia).where(Frequencia.matricula_id == matricula_id)
    return list(db.scalars(stmt.order_by(Frequencia.data)).all())


def resumo_frequencia(db: Session, matricula_id: uuid.UUID) -> FrequenciaResumo:
    """% de frequência = presenças / dias letivos registrados, vs mínimo da escola."""
    base = _ativos(Frequencia).where(Frequencia.matricula_id == matricula_id)
    dias_letivos = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    presencas = (
        db.scalar(
            select(func.count()).select_from(
                base.where(Frequencia.presente.is_(True)).subquery()
            )
        )
        or 0
    )
    justificadas = (
        db.scalar(
            select(func.count()).select_from(
                base.where(Frequencia.justificada.is_(True)).subquery()
            )
        )
        or 0
    )
    faltas = dias_letivos - presencas

    if dias_letivos > 0:
        percentual = (Decimal(presencas) / Decimal(dias_letivos) * Decimal(100)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
    else:
        percentual = Decimal("0.00")

    config = obter_ou_criar_config(db)
    minima = Decimal(config.frequencia_minima_percentual)
    return FrequenciaResumo(
        matricula_id=matricula_id,
        dias_letivos=dias_letivos,
        presencas=presencas,
        faltas=faltas,
        faltas_justificadas=justificadas,
        percentual=percentual,
        frequencia_minima=minima,
        # Sem dias letivos ainda, não há como afirmar suficiência.
        suficiente=dias_letivos > 0 and percentual >= minima,
    )
