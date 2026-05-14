from __future__ import annotations

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from api_testing.backend.api.schemas.common import ErrorDetail, ErrorResponse
from api_testing.backend.domain.errors import ArtifactNotFound, InvalidArtifactRequest


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ArtifactNotFound)
    async def artifact_not_found_handler(_, exc: ArtifactNotFound) -> JSONResponse:
        return error_response(404, "not_found", str(exc))

    @app.exception_handler(InvalidArtifactRequest)
    async def invalid_artifact_request_handler(
        _, exc: InvalidArtifactRequest
    ) -> JSONResponse:
        return error_response(400, "invalid_request", str(exc))

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_, exc: RequestValidationError) -> JSONResponse:
        return error_response(422, "validation_error", _validation_message(exc))


def error_response(status_code: int, code: str, message: str) -> JSONResponse:
    body = ErrorResponse(error=ErrorDetail(code=code, message=message))
    return JSONResponse(status_code=status_code, content=body.model_dump())


def _validation_message(exc: RequestValidationError) -> str:
    messages = []
    for error in exc.errors():
        location = ".".join(str(part) for part in error.get("loc", ()))
        message = str(error.get("msg", "Invalid value"))
        messages.append(f"{location}: {message}" if location else message)
    return "; ".join(messages) or "Request validation failed"
