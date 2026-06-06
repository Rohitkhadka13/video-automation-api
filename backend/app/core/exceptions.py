# =============================================================================
# app/core/exceptions.py
# Domain and HTTP exception hierarchy.
#
# Design principle:
#   - Domain exceptions: plain Python exceptions raised in domain/service layer.
#     They carry no HTTP knowledge — only business meaning.
#   - HTTP exceptions: FastAPI HTTPException subclasses raised in the API layer
#     (endpoints, deps). These are translated from domain exceptions by handlers
#     registered in app/main.py.
#
# This keeps the domain clean: a domain service never imports from fastapi.
# =============================================================================
from __future__ import annotations

from fastapi import HTTPException, status


# =============================================================================
# Domain exceptions — no HTTP status codes, no FastAPI imports
# =============================================================================

class AppError(Exception):
    """Base class for all application-specific exceptions."""

    def __init__(self, message: str = "An unexpected error occurred") -> None:
        self.message = message
        super().__init__(message)

    def __repr__(self) -> str:
        return f"{type(self).__name__}(message={self.message!r})"


# ---------------------------------------------------------------------------
# Authentication & authorisation
# ---------------------------------------------------------------------------

class AuthenticationError(AppError):
    """Raised when credentials are invalid or missing."""


class ExpiredTokenError(AuthenticationError):
    """Raised when a JWT token has expired."""


class InvalidTokenError(AuthenticationError):
    """Raised when a JWT token is malformed or has an invalid signature."""


class InsufficientPermissionsError(AppError):
    """Raised when an authenticated user lacks the required permissions."""


# ---------------------------------------------------------------------------
# Resource errors
# ---------------------------------------------------------------------------

class NotFoundError(AppError):
    """Raised when a requested resource does not exist."""

    def __init__(self, resource: str = "Resource", identifier: str | int | None = None) -> None:
        id_part = f" with id '{identifier}'" if identifier is not None else ""
        super().__init__(f"{resource}{id_part} not found")
        self.resource = resource
        self.identifier = identifier


class AlreadyExistsError(AppError):
    """Raised when a resource with the given identifier already exists."""

    def __init__(self, resource: str = "Resource", field: str = "identifier") -> None:
        super().__init__(f"{resource} with this {field} already exists")
        self.resource = resource
        self.field = field


class ConflictError(AppError):
    """Raised when an operation conflicts with the current resource state."""


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------

class ValidationError(AppError):
    """Raised when business-rule validation fails (not Pydantic schema validation)."""

    def __init__(self, message: str, field: str | None = None) -> None:
        super().__init__(message)
        self.field = field


class FileTooLargeError(ValidationError):
    """Raised when an uploaded file exceeds the maximum allowed size."""

    def __init__(self, max_size_mb: int, actual_size_mb: float) -> None:
        super().__init__(
            f"File size {actual_size_mb:.1f}MB exceeds maximum of {max_size_mb}MB"
        )
        self.max_size_mb = max_size_mb
        self.actual_size_mb = actual_size_mb


class InvalidFileTypeError(ValidationError):
    """Raised when an uploaded file has an unsupported MIME type or extension."""

    def __init__(self, allowed: list[str], received: str) -> None:
        super().__init__(
            f"File type '{received}' is not allowed. Allowed types: {', '.join(allowed)}"
        )
        self.allowed = allowed
        self.received = received


# ---------------------------------------------------------------------------
# Processing errors
# ---------------------------------------------------------------------------

class ProcessingError(AppError):
    """Raised when a video/audio processing task fails."""


class FFmpegError(ProcessingError):
    """Raised when an FFmpeg command exits with a non-zero status."""

    def __init__(self, command: str, returncode: int, stderr: str) -> None:
        super().__init__(f"FFmpeg failed (exit {returncode}): {stderr[:500]}")
        self.command = command
        self.returncode = returncode
        self.stderr = stderr


class WhisperError(ProcessingError):
    """Raised when Whisper transcription fails."""


class PiperError(ProcessingError):
    """Raised when Piper TTS synthesis fails."""


class OllamaError(ProcessingError):
    """Raised when the Ollama API returns an error or times out."""


# ---------------------------------------------------------------------------
# Storage errors
# ---------------------------------------------------------------------------

class StorageError(AppError):
    """Raised when a file storage operation fails."""


class FileNotFoundInStorageError(StorageError):
    """Raised when a file cannot be found in the storage backend."""


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------

class RateLimitExceededError(AppError):
    """Raised when a user exceeds the allowed request rate."""

    def __init__(self, retry_after: int = 60) -> None:
        super().__init__("Rate limit exceeded. Please try again later.")
        self.retry_after = retry_after


# =============================================================================
# HTTP exceptions — raised in the API layer (endpoints / deps)
# These are thin wrappers around FastAPI's HTTPException for consistent
# JSON error responses across the entire API.
# =============================================================================

class HTTP400BadRequest(HTTPException):
    def __init__(self, detail: str = "Bad request") -> None:
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class HTTP401Unauthorized(HTTPException):
    def __init__(self, detail: str = "Not authenticated") -> None:
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class HTTP403Forbidden(HTTPException):
    def __init__(self, detail: str = "Insufficient permissions") -> None:
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class HTTP404NotFound(HTTPException):
    def __init__(self, detail: str = "Resource not found") -> None:
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class HTTP409Conflict(HTTPException):
    def __init__(self, detail: str = "Resource already exists") -> None:
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)


class HTTP413RequestEntityTooLarge(HTTPException):
    def __init__(self, detail: str = "Request entity too large") -> None:
        super().__init__(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=detail
        )


class HTTP422UnprocessableEntity(HTTPException):
    def __init__(self, detail: str = "Validation error") -> None:
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail
        )


class HTTP429TooManyRequests(HTTPException):
    def __init__(self, detail: str = "Too many requests", retry_after: int = 60) -> None:
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
            headers={"Retry-After": str(retry_after)},
        )


class HTTP500InternalServerError(HTTPException):
    def __init__(self, detail: str = "Internal server error") -> None:
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail
        )


class HTTP503ServiceUnavailable(HTTPException):
    def __init__(self, detail: str = "Service temporarily unavailable") -> None:
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail
        )


# =============================================================================
# Domain → HTTP exception mapper
# Used in exception handlers registered in app/main.py
# =============================================================================
_DOMAIN_TO_HTTP: dict[type[AppError], type[HTTPException]] = {
    AuthenticationError:         HTTP401Unauthorized,
    ExpiredTokenError:           HTTP401Unauthorized,
    InvalidTokenError:           HTTP401Unauthorized,
    InsufficientPermissionsError: HTTP403Forbidden,
    NotFoundError:               HTTP404NotFound,
    AlreadyExistsError:          HTTP409Conflict,
    ConflictError:               HTTP409Conflict,
    ValidationError:             HTTP400BadRequest,
    FileTooLargeError:           HTTP413RequestEntityTooLarge,
    InvalidFileTypeError:        HTTP422UnprocessableEntity,
    ProcessingError:             HTTP500InternalServerError,
    StorageError:                HTTP500InternalServerError,
    RateLimitExceededError:      HTTP429TooManyRequests,
}


def domain_exception_to_http(exc: AppError) -> HTTPException:
    """
    Convert a domain exception to its corresponding HTTP exception.
    Falls back to HTTP 500 for unmapped exceptions.
    """
    http_cls = _DOMAIN_TO_HTTP.get(type(exc), HTTP500InternalServerError)

    # Special handling for rate limit (adds Retry-After header)
    if isinstance(exc, RateLimitExceededError):
        return HTTP429TooManyRequests(detail=exc.message, retry_after=exc.retry_after)

    return http_cls(detail=exc.message)