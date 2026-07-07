"""Erros estruturados: toda resposta de erro sai como JSON (nunca texto solto).

Formato padrão:
    {"erro": {"codigo": "<slug>", "mensagem": "<texto>", "detalhes": <opcional>}}
"""

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(Exception):
    """Erro de aplicação com código estável e status HTTP.

    NÃO colocar dado pessoal (CPF, endereço, financeiro) na mensagem.
    """

    def __init__(
        self,
        codigo: str,
        mensagem: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        detalhes: Any | None = None,
    ) -> None:
        super().__init__(mensagem)
        self.codigo = codigo
        self.mensagem = mensagem
        self.status_code = status_code
        self.detalhes = detalhes


def _payload(codigo: str, mensagem: str, detalhes: Any | None = None) -> dict[str, Any]:
    corpo: dict[str, Any] = {"codigo": codigo, "mensagem": mensagem}
    if detalhes is not None:
        corpo["detalhes"] = detalhes
    return {"erro": corpo}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_payload(exc.codigo, exc.mensagem, exc.detalhes),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _handle_http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_payload("http_error", str(exc.detail)),
        )

    @app.exception_handler(RequestValidationError)
    async def _handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_payload(
                "validacao",
                "Dados de entrada inválidos.",
                jsonable_encoder(exc.errors()),
            ),
        )
