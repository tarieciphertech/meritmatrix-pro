"""
Application-level exceptions and centralized FastAPI exception handlers.

Design goal: users never see raw Python/SQL exceptions. Every error
response has a consistent shape:

    {
        "error": {
            "code": "STUDENT_ID_ALREADY_EXISTS",
            "message": "That student ID is already registered."
        }
    }

Technical details are logged server-side only.
"""
import logging
import uuid

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("meritmatrix.errors")


class AppError(Exception):
    """Base class for expected, user-facing application errors."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "APP_ERROR"

    def __init__(self, message: str, *, code: str | None = None, status_code: int | None = None):
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        if status_code:
            self.status_code = status_code


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "NOT_FOUND"


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT
    code = "CONFLICT"


class UnauthorizedError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "UNAUTHORIZED"


class ForbiddenError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "FORBIDDEN"


def _error_body(code: str, message: str, request_id: str | None = None) -> dict:
    body = {"error": {"code": code, "message": message}}
    if request_id:
        body["error"]["request_id"] = request_id
    return body


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError):
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(exc.code, exc.message),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_error_body(
                "VALIDATION_ERROR",
                "The submitted data is invalid. Please check the fields and try again.",
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, exc: StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body("HTTP_ERROR", str(exc.detail)),
        )

    @app.exception_handler(IntegrityError)
    async def handle_integrity_error(request: Request, exc: IntegrityError):
        request_id = str(uuid.uuid4())
        logger.error("IntegrityError [%s]: %s", request_id, exc, exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=_error_body(
                "DUPLICATE_OR_CONSTRAINT_VIOLATION",
                "This record conflicts with an existing one (e.g. a duplicate ID).",
                request_id,
            ),
        )

    @app.exception_handler(SQLAlchemyError)
    async def handle_sqlalchemy_error(request: Request, exc: SQLAlchemyError):
        request_id = str(uuid.uuid4())
        logger.error("Database error [%s]: %s", request_id, exc, exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_body(
                "DATABASE_ERROR",
                "A database error occurred. Please try again later.",
                request_id,
            ),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception):
        request_id = str(uuid.uuid4())
        logger.error("Unhandled exception [%s]: %s", request_id, exc, exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_body(
                "INTERNAL_SERVER_ERROR",
                "An unexpected error occurred. Please try again later.",
                request_id,
            ),
        )
