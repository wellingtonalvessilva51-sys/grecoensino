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

from src.core import audit
from src.core.exceptions import AppError
from src.modules.academico.models import (
    AnoLetivo,
    ConfigAcademica,
    Curso,
    Disciplina,
    Frequencia,
    Matricula,
    Nota,
    Serie,
    Turma,
    TurmaDisciplinaProfessor,
)
from src.modules.academico.schemas import (
    AnoLetivoCreate,
    AtribuicaoCreate,
    BoletimDisciplina,
    BoletimRead,
    ConfigAcademicaUpdate,
    CursoCreate,
    DisciplinaCreate,
    FrequenciaCreate,
    FrequenciaResumo,
    MatriculaCreate,
    NotaCreate,
    SerieCreate,
    TurmaCreate,
)
from src.modules.financeiro import service as financeiro
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
def criar_matricula(db: Session, dados: MatriculaCreate, principal=None) -> Matricula:
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

    # Efeito entre módulos por chamada de serviço síncrona (§6): se a matrícula
    # informou cobrança inicial, gera o título de mensalidade. Sem principal
    # (chamada interna sem usuário) não há como auditar, então não gera.
    if dados.cobranca_inicial is not None and principal is not None:
        financeiro.gerar_titulo_matricula(
            db,
            principal,
            aluno_id=obj.aluno_id,
            competencia=dados.cobranca_inicial.competencia,
            vencimento=dados.cobranca_inicial.vencimento,
            valor=dados.cobranca_inicial.valor,
        )

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


# --- Notas (por período e disciplina) ---------------------------------------
def professor_leciona_disciplina(
    db: Session, principal, turma_id: uuid.UUID, disciplina_id: uuid.UUID
) -> bool:
    """True se o principal pode lançar nota: privilegiado ou professor daquela
    disciplina naquela turma (ACL mais fina que a de frequência)."""
    if PAPEIS_LANCA_PRIVILEGIADO.intersection(principal.papeis):
        return True
    minha = pessoas.pessoa_do_usuario(db, principal.usuario.id)
    if minha is None:
        return False
    vinculo = db.scalars(
        _ativos(TurmaDisciplinaProfessor).where(
            TurmaDisciplinaProfessor.turma_id == turma_id,
            TurmaDisciplinaProfessor.disciplina_id == disciplina_id,
            TurmaDisciplinaProfessor.professor_id == minha.id,
        )
    ).first()
    return vinculo is not None


def registrar_nota(db: Session, principal, dados: NotaCreate) -> Nota:
    matricula = _obter(db, Matricula, dados.matricula_id)
    if matricula is None:
        raise AppError("matricula_inexistente", "Matrícula não encontrada.", status_code=404)
    if _obter(db, Disciplina, dados.disciplina_id) is None:
        raise AppError("disciplina_inexistente", "Disciplina não encontrada.", status_code=404)

    config = obter_ou_criar_config(db)
    if dados.periodo > config.num_periodos:
        raise AppError(
            "periodo_invalido",
            f"Período {dados.periodo} fora da configuração da escola (1..{config.num_periodos}).",
            status_code=400,
        )
    if not professor_leciona_disciplina(db, principal, matricula.turma_id, dados.disciplina_id):
        raise AppError(
            "sem_permissao_disciplina",
            "Professor não leciona esta disciplina nesta turma.",
            status_code=403,
        )

    valor = float(dados.valor)
    depois = {"disciplina_id": str(dados.disciplina_id), "periodo": dados.periodo, "valor": valor}

    # Upsert por (matrícula, disciplina, período): relançar atualiza + audita.
    existente = db.scalars(
        _ativos(Nota).where(
            Nota.matricula_id == dados.matricula_id,
            Nota.disciplina_id == dados.disciplina_id,
            Nota.periodo == dados.periodo,
        )
    ).first()
    if existente is not None:
        antes = {
            "disciplina_id": str(existente.disciplina_id),
            "periodo": existente.periodo,
            "valor": float(existente.valor),
        }
        existente.valor = dados.valor
        audit.registrar(
            db,
            acao="atualizar",
            entidade="nota",
            entidade_id=existente.id,
            usuario_id=principal.usuario.id,
            dados_antes=antes,
            dados_depois=depois,
        )
        db.commit()
        db.refresh(existente)
        return existente

    obj = Nota(
        matricula_id=dados.matricula_id,
        disciplina_id=dados.disciplina_id,
        periodo=dados.periodo,
        valor=dados.valor,
    )
    db.add(obj)
    db.flush()  # id disponível para a auditoria
    audit.registrar(
        db,
        acao="criar",
        entidade="nota",
        entidade_id=obj.id,
        usuario_id=principal.usuario.id,
        dados_depois=depois,
    )
    db.commit()
    db.refresh(obj)
    return obj


def listar_notas(db: Session, matricula_id: uuid.UUID) -> list[Nota]:
    stmt = _ativos(Nota).where(Nota.matricula_id == matricula_id)
    return list(db.scalars(stmt.order_by(Nota.disciplina_id, Nota.periodo)).all())


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


# --- Boletim (consolida as duas regras configuráveis da escola) -------------
def _quantizar(valor: Decimal) -> Decimal:
    # Arredondamento padrão (2 casas, HALF_UP). TODO: confirmar regra com a escola-piloto.
    return valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _situacao_final(disciplinas: list[BoletimDisciplina], freq: FrequenciaResumo) -> str:
    if not disciplinas or any(d.situacao == "cursando" for d in disciplinas):
        return "cursando"
    if freq.dias_letivos == 0:
        return "cursando"  # sem frequência lançada não dá pra fechar
    if not freq.suficiente:
        return "reprovado_frequencia"
    if all(d.situacao == "aprovado" for d in disciplinas):
        return "aprovado"
    return "reprovado_nota"


def montar_boletim(db: Session, matricula_id: uuid.UUID) -> BoletimRead:
    """Calcula (não persiste) média anual ponderada por disciplina e a situação
    final, combinando média mínima E frequência mínima da config da escola."""
    config = obter_ou_criar_config(db)
    media_minima = Decimal(config.media_minima)
    num_periodos = config.num_periodos
    pesos = [Decimal(str(p)) for p in config.pesos_periodos]

    por_disciplina: dict[uuid.UUID, list[Nota]] = {}
    for nota in listar_notas(db, matricula_id):
        por_disciplina.setdefault(nota.disciplina_id, []).append(nota)

    disciplinas: list[BoletimDisciplina] = []
    for disc_id, notas in por_disciplina.items():
        soma_pond = Decimal(0)
        soma_peso = Decimal(0)
        periodos = set()
        for nota in notas:
            idx = nota.periodo - 1
            peso = pesos[idx] if 0 <= idx < len(pesos) else Decimal(1)
            soma_pond += Decimal(nota.valor) * peso
            soma_peso += peso
            periodos.add(nota.periodo)

        media = _quantizar(soma_pond / soma_peso) if soma_peso > 0 else Decimal("0.00")
        completa = len(periodos) == num_periodos
        if not completa:
            situacao = "cursando"
        elif media >= media_minima:
            situacao = "aprovado"
        else:
            situacao = "reprovado_nota"

        disciplinas.append(
            BoletimDisciplina(
                disciplina_id=disc_id,
                media=media,
                periodos_lancados=len(periodos),
                completa=completa,
                situacao=situacao,
            )
        )

    disciplinas.sort(key=lambda d: str(d.disciplina_id))  # saída estável
    freq = resumo_frequencia(db, matricula_id)
    return BoletimRead(
        matricula_id=matricula_id,
        media_minima=media_minima,
        num_periodos=num_periodos,
        disciplinas=disciplinas,
        frequencia=freq,
        situacao_final=_situacao_final(disciplinas, freq),
    )
