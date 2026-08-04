"""
Global exception handlers and application exception hierarchy.

Architecture principle:
  Route handlers raise exceptions. They NEVER construct error responses directly.
  Exception handlers here translate exceptions into consistent HTTP responses.

Exception hierarchy:
  Exception (Python built-in)
    └── AppException (base for all domain errors)
          ├── NotFoundError       → 404
          ├── ConflictError       → 409
          └── ValidationAppError  → 422

  FastAPI RequestValidationError    → 422 (request body/query param errors)
  Exception (catch-all)             → 500

Why consistent error envelopes?
  The frontend and API consumers deserve predictable error shapes.
  Every error response follows the same structure:
    {
      "error": {
        "message": "Human-readable description",
        "code":    "MACHINE_READABLE_CODE",
        "detail":  {}  // optional structured context
      }
    }

Evolution plan:
  - Phase 2: Add DatabaseError, IntegrityError wrappers
  - Phase 4: Add AuthenticationError, AuthorizationError
"""

import structlog
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = structlog.get_logger(__name__)


# =============================================================================
# Application Exception Hierarchy
# =============================================================================


class AppException(Exception):
    """
    Base exception for all application-domain errors.

    Subclass this for every error type the application can produce.
    Never raise AppException directly — always raise a specific subclass.
    """

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail: dict | None = None,
    ) -> None:
        self.message = message
        self.code = code
        self.status_code = status_code
        self.detail = detail or {}
        super().__init__(message)


class NotFoundError(AppException):
    """Raised when a requested resource does not exist."""

    def __init__(self, resource: str, identifier: str | int) -> None:
        super().__init__(
            message=f"{resource} '{identifier}' was not found.",
            code="NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class ConflictError(AppException):
    """Raised when a create/update operation violates a uniqueness constraint."""

    def __init__(self, message: str, detail: dict | None = None) -> None:
        super().__init__(
            message=message,
            code="CONFLICT",
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
        )


class ValidationAppError(AppException):
    """Raised when data passes schema validation but violates a business rule."""

    def __init__(self, message: str, detail: dict | None = None) -> None:
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=detail,
        )


class IngestionError(AppException):
    """Raised when a document cannot be parsed or processed."""

    def __init__(self, message: str, detail: dict | None = None) -> None:
        super().__init__(
            message=message,
            code="INGESTION_FAILED",
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=detail,
        )


class ProviderError(AppException):
    """Raised when the configured Gemini provider rejects a request."""

    def __init__(self, message: str, detail: dict | None = None) -> None:
        super().__init__(
            message=message,
            code="PROVIDER_ERROR",
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=detail,
        )


class ProviderTimeoutError(AppException):
    """Raised when a Gemini operation does not complete in time."""

    def __init__(self, message: str = "The AI provider timed out.") -> None:
        super().__init__(
            message=message,
            code="PROVIDER_TIMEOUT",
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
        )


class UnsupportedFileTypeError(AppException):
    """Raised for file extensions outside the supported Phase 2 set."""

    def __init__(self, file_name: str) -> None:
        super().__init__(
            message=f"The file type for '{file_name}' is not supported.",
            code="UNSUPPORTED_FILE_TYPE",
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        )


class FileTooLargeError(AppException):
    """Raised when an upload exceeds the configured maximum size."""

    def __init__(self, maximum_bytes: int) -> None:
        super().__init__(
            message="The uploaded file exceeds the maximum allowed size.",
            code="FILE_TOO_LARGE",
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail={"maximum_bytes": maximum_bytes},
        )


# =============================================================================
# Exception Handler Registration
# =============================================================================


def _error_body(message: str, code: str, detail: dict) -> dict:
    """Build the standard error response envelope."""
    return {"error": {"message": message, "code": code, "detail": detail}}


def register_exception_handlers(app: FastAPI) -> None:
    """
    Attach all exception handlers to the FastAPI application instance.

    Call this once in the application factory, after the app is created.
    The order of registration matters: more specific handlers first.
    """

    @app.exception_handler(AppException)
    async def handle_app_exception(request: Request, exc: AppException) -> JSONResponse:
        """Handle all application-domain exceptions."""
        logger.warning(
            "app_exception",
            path=str(request.url.path),
            method=request.method,
            status_code=exc.status_code,
            error_code=exc.code,
            message=exc.message,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(exc.message, exc.code, exc.detail),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Handle Pydantic request validation failures (body, query params, etc.)."""
        logger.warning(
            "request_validation_error",
            path=str(request.url.path),
            method=request.method,
            errors=exc.errors(),
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content=_error_body(
                message="Request validation failed.",
                code="VALIDATION_ERROR",
                detail={"errors": exc.errors()},
            ),
        )

    @app.exception_handler(Exception)
    async def handle_unhandled_exception(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """
        Catch-all handler for unexpected exceptions.

        Logs the full traceback but returns a generic message to the client
        to avoid leaking internal implementation details.
        """
        logger.exception(
            "unhandled_exception",
            path=str(request.url.path),
            method=request.method,
            exc_type=type(exc).__name__,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_body(
                message="An unexpected error occurred. Please try again later.",
                code="INTERNAL_ERROR",
                detail={},
            ),
        )
