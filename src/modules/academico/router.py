"""Rotas do Acadêmico: estrutura curricular, atribuições e matrícula.

Escrita: RBAC secretaria/admin_tenant. Leitura da estrutura: autenticado.
Leitura de matrícula: filtrada por ACL (responsável só vê o próprio dependente).
"""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.exceptions import AppError
from src.modules.academico import service
from src.modules.academico.schemas import (
    AnoLetivoCreate,
    AnoLetivoRead,
    AtribuicaoCreate,
    AtribuicaoRead,
    ConfigAcademicaRead,
    ConfigAcademicaUpdate,
    CursoCreate,
    CursoRead,
    DisciplinaCreate,
    DisciplinaRead,
    FrequenciaCreate,
    FrequenciaRead,
    FrequenciaResumo,
    MatriculaCreate,
    MatriculaRead,
    NotaCreate,
    NotaRead,
    SerieCreate,
    SerieRead,
    TurmaCreate,
    TurmaRead,
)
from src.shared.deps import Principal, get_current_user, require_papel

router = APIRouter(prefix="/academico", tags=["academico"])

_ESCRITA = require_papel("secretaria", "admin_tenant")
_CONFIG = require_papel("admin_tenant", "secretaria")
# Lançamento de frequência: professor (restrito à sua turma pela ACL do service),
# secretaria e admin_tenant.
_LANCA = require_papel("professor", "secretaria", "admin_tenant")
_CRIADO = status.HTTP_201_CREATED


# --- Configuração acadêmica (regras por escola) -----------------------------
@router.get("/config", response_model=ConfigAcademicaRead)
def obter_config(db: Session = Depends(get_db), _: Principal = Depends(get_current_user)):
    return service.obter_ou_criar_config(db)


@router.put("/config", response_model=ConfigAcademicaRead)
def atualizar_config(
    dados: ConfigAcademicaUpdate,
    db: Session = Depends(get_db),
    _: Principal = Depends(_CONFIG),
):
    return service.atualizar_config(db, dados)


# --- Ano letivo -------------------------------------------------------------
@router.post("/anos-letivos", response_model=AnoLetivoRead, status_code=_CRIADO)
def criar_ano_letivo(dados: AnoLetivoCreate, db: Session = Depends(get_db), _: Principal = Depends(_ESCRITA)):
    return service.criar_ano_letivo(db, dados)


@router.get("/anos-letivos", response_model=list[AnoLetivoRead])
def listar_anos_letivos(db: Session = Depends(get_db), _: Principal = Depends(get_current_user)):
    return service.listar_anos_letivos(db)


# --- Curso ------------------------------------------------------------------
@router.post("/cursos", response_model=CursoRead, status_code=_CRIADO)
def criar_curso(dados: CursoCreate, db: Session = Depends(get_db), _: Principal = Depends(_ESCRITA)):
    return service.criar_curso(db, dados)


@router.get("/cursos", response_model=list[CursoRead])
def listar_cursos(db: Session = Depends(get_db), _: Principal = Depends(get_current_user)):
    return service.listar_cursos(db)


# --- Série ------------------------------------------------------------------
@router.post("/series", response_model=SerieRead, status_code=_CRIADO)
def criar_serie(dados: SerieCreate, db: Session = Depends(get_db), _: Principal = Depends(_ESCRITA)):
    return service.criar_serie(db, dados)


@router.get("/series", response_model=list[SerieRead])
def listar_series(
    curso_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    _: Principal = Depends(get_current_user),
):
    return service.listar_series(db, curso_id)


# --- Disciplina -------------------------------------------------------------
@router.post("/disciplinas", response_model=DisciplinaRead, status_code=_CRIADO)
def criar_disciplina(dados: DisciplinaCreate, db: Session = Depends(get_db), _: Principal = Depends(_ESCRITA)):
    return service.criar_disciplina(db, dados)


@router.get("/disciplinas", response_model=list[DisciplinaRead])
def listar_disciplinas(db: Session = Depends(get_db), _: Principal = Depends(get_current_user)):
    return service.listar_disciplinas(db)


# --- Turma ------------------------------------------------------------------
@router.post("/turmas", response_model=TurmaRead, status_code=_CRIADO)
def criar_turma(dados: TurmaCreate, db: Session = Depends(get_db), _: Principal = Depends(_ESCRITA)):
    return service.criar_turma(db, dados)


@router.get("/turmas", response_model=list[TurmaRead])
def listar_turmas(db: Session = Depends(get_db), _: Principal = Depends(get_current_user)):
    return service.listar_turmas(db)


@router.get("/turmas/{turma_id}", response_model=TurmaRead)
def obter_turma(turma_id: uuid.UUID, db: Session = Depends(get_db), _: Principal = Depends(get_current_user)):
    turma = service.obter_turma(db, turma_id)
    if turma is None:
        raise AppError("turma_inexistente", "Turma não encontrada.", status_code=404)
    return turma


# --- Atribuição disciplina/professor ----------------------------------------
@router.post("/turmas/{turma_id}/disciplinas", response_model=AtribuicaoRead, status_code=_CRIADO)
def atribuir_disciplina(
    turma_id: uuid.UUID,
    dados: AtribuicaoCreate,
    db: Session = Depends(get_db),
    _: Principal = Depends(_ESCRITA),
):
    return service.atribuir_disciplina(db, turma_id, dados)


@router.get("/turmas/{turma_id}/disciplinas", response_model=list[AtribuicaoRead])
def listar_atribuicoes(turma_id: uuid.UUID, db: Session = Depends(get_db), _: Principal = Depends(get_current_user)):
    return service.listar_atribuicoes(db, turma_id)


# --- Matrícula --------------------------------------------------------------
@router.post("/matriculas", response_model=MatriculaRead, status_code=_CRIADO)
def criar_matricula(dados: MatriculaCreate, db: Session = Depends(get_db), _: Principal = Depends(_ESCRITA)):
    return service.criar_matricula(db, dados)


@router.get("/matriculas", response_model=list[MatriculaRead])
def listar_matriculas(db: Session = Depends(get_db), principal: Principal = Depends(get_current_user)):
    return service.listar_matriculas(db, principal)


@router.get("/matriculas/{matricula_id}", response_model=MatriculaRead)
def obter_matricula(
    matricula_id: uuid.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_user),
):
    matricula = service.obter_matricula(db, matricula_id)
    if matricula is None or not service.pode_ver_matricula(db, principal, matricula):
        raise AppError("matricula_nao_encontrada", "Matrícula não encontrada.", status_code=404)
    return matricula


# --- Notas (por período e disciplina) ---------------------------------------
@router.post("/notas", response_model=NotaRead, status_code=_CRIADO)
def registrar_nota(
    dados: NotaCreate,
    db: Session = Depends(get_db),
    principal: Principal = Depends(_LANCA),
):
    return service.registrar_nota(db, principal, dados)


# --- Frequência (diária, por dia letivo) ------------------------------------
def _matricula_visivel(db: Session, principal: Principal, matricula_id: uuid.UUID):
    """Carrega a matrícula respeitando a ACL de leitura, senão 404 (não vaza existência)."""
    matricula = service.obter_matricula(db, matricula_id)
    if matricula is None or not service.pode_ver_matricula(db, principal, matricula):
        raise AppError("matricula_nao_encontrada", "Matrícula não encontrada.", status_code=404)
    return matricula


@router.post("/frequencias", response_model=FrequenciaRead, status_code=_CRIADO)
def registrar_frequencia(
    dados: FrequenciaCreate,
    db: Session = Depends(get_db),
    principal: Principal = Depends(_LANCA),
):
    return service.registrar_frequencia(db, principal, dados)


@router.get(
    "/matriculas/{matricula_id}/frequencias", response_model=list[FrequenciaRead]
)
def listar_frequencias(
    matricula_id: uuid.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_user),
):
    _matricula_visivel(db, principal, matricula_id)
    return service.listar_frequencias(db, matricula_id)


@router.get(
    "/matriculas/{matricula_id}/frequencia-resumo", response_model=FrequenciaResumo
)
def resumo_frequencia(
    matricula_id: uuid.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_user),
):
    _matricula_visivel(db, principal, matricula_id)
    return service.resumo_frequencia(db, matricula_id)


@router.get("/matriculas/{matricula_id}/notas", response_model=list[NotaRead])
def listar_notas(
    matricula_id: uuid.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_user),
):
    _matricula_visivel(db, principal, matricula_id)
    return service.listar_notas(db, matricula_id)
