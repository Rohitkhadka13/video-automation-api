# =============================================================================
# app/main.py
# FastAPI application factory with lifespan, middleware, and exception handlers.
# This is the single entry point: uvicorn app.main:app
# =============================================================================
from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager
from typing import AsyncIterator

import sentry_sdk
from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.exceptions import AppError, domain_exception_to_http
from app.core.logging import (
    bind_request_context,
    clear_request_context,
    configure_logging,
    get_logger,
)

logger = get_logger(__name__)

dsn = (settings.SENTRY_DSN or "").strip()

# =============================================================================
# Lifespan — startup and shutdown hooks
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Application lifespan manager.
    Code before `yield` runs on startup; code after runs on shutdown.
    """
    # ------------------------------------------------------------------
    # Startup
    # ------------------------------------------------------------------
    configure_logging()
    logger.info("app.startup", version=settings.APP_VERSION, env=settings.APP_ENV)

    # Initialise Sentry before anything else so startup errors are captured
    if dsn and dsn.startswith("http"):
        sentry_sdk.init(
        dsn=dsn,
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        environment=settings.APP_ENV,
        release=settings.APP_VERSION,
    )
    logger.info("sentry.initialised")

    # Warm up the database connection pool
    from app.db.session import open_db_connection
    await open_db_connection()
    logger.info("db.pool.ready")

    # Seed initial superuser if the DB is empty
    from app.db.init_db import init_db
    from app.db.session import get_db_context
    async with get_db_context() as db:
        await init_db(db)

    logger.info("app.ready", host=settings.API_HOST, port=settings.API_PORT)

    yield

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------
    logger.info("app.shutdown")
    from app.db.session import close_db_connection
    await close_db_connection()
    logger.info("db.pool.closed")


# =============================================================================
# App factory
# =============================================================================

def create_app() -> FastAPI:
    """Build and configure the FastAPI application instance."""

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "AI Video Automation SaaS — REST API.\n\n"
            "Authenticate via `POST /api/v1/auth/login` to get a Bearer token, "
            "then include it in the `Authorization: Bearer <token>` header."
        ),
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )

    _register_middleware(app)
    _register_exception_handlers(app)
    _register_routers(app)

    return app


# =============================================================================
# Middleware
# =============================================================================

def _register_middleware(app: FastAPI) -> None:
    """Register all middleware in the correct order (outermost first)."""

    # GZip — compress responses > 1KB
    app.add_middleware(GZipMiddleware, minimum_size=1024)

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(o) for o in settings.CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Process-Time"],
    )

    # Request ID + structured logging + timing
    app.add_middleware(RequestContextMiddleware)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    Per-request middleware that:
      1. Assigns a unique X-Request-ID to every request.
      2. Binds request context to structlog (request_id, path, method).
      3. Adds X-Process-Time header to every response.
      4. Clears structlog context after the request.
    """

    async def dispatch(self, request: Request, call_next: object) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        start = time.perf_counter()

        bind_request_context(
            request_id=request_id,
            path=request.url.path,
            method=request.method,
        )

        try:
            response: Response = await call_next(request)  # type: ignore[arg-type]
        except Exception:
            clear_request_context()
            raise

        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = f"{elapsed_ms}ms"

        logger.info(
            "http.request",
            status_code=response.status_code,
            elapsed_ms=elapsed_ms,
        )

        clear_request_context()
        return response


# =============================================================================
# Exception handlers
# =============================================================================

def _register_exception_handlers(app: FastAPI) -> None:
    """Map exceptions to JSON error responses."""

    @app.exception_handler(AppError)
    async def handle_domain_error(request: Request, exc: AppError) -> JSONResponse:
        """Convert domain exceptions to HTTP responses."""
        http_exc = domain_exception_to_http(exc)
        return JSONResponse(
            status_code=http_exc.status_code,
            content={"detail": http_exc.detail},
            headers=getattr(http_exc, "headers", None),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Return structured validation errors from Pydantic."""
        errors = []
        for error in exc.errors():
            errors.append({
                "field": " → ".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            })
        return JSONResponse(
            status_code=422,
            content={"detail": "Validation error", "errors": errors},
        )

    @app.exception_handler(Exception)
    async def handle_unhandled_error(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """Catch-all: log the exception and return a generic 500."""
        logger.exception(
            "http.unhandled_error",
            exc_type=type(exc).__name__,
            exc_message=str(exc),
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "An unexpected error occurred"},
        )


# =============================================================================
# Routers
# =============================================================================

def _register_routers(app: FastAPI) -> None:
    """Mount all API routers."""
    from app.api.v1.router import router as v1_router

    app.include_router(v1_router, prefix="/api/v1")

    # Health check — no auth, no rate limiting, always returns 200 when alive
    @app.get("/health", tags=["system"], include_in_schema=False)
    async def health_check() -> dict:
        from app.db.session import check_db_health
        db_ok = await check_db_health()
        return {
            "status": "healthy" if db_ok else "degraded",
            "version": settings.APP_VERSION,
            "env": settings.APP_ENV,
            "db": "ok" if db_ok else "error",
        }


# =============================================================================
# Module-level app instance (imported by uvicorn)
# =============================================================================
app: FastAPI = create_app()