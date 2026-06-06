# =============================================================================
# tests/conftest.py
# Shared pytest fixtures for the entire test suite.
#
# Architecture:
#   - All DB tests run in a transaction that is rolled back after each test.
#   - A single test database is created once per session and reused.
#   - The FastAPI app is overridden to use the test DB session.
#   - Mock objects are provided for Celery, Ollama, Whisper, and Piper.
# =============================================================================
from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

# ---------------------------------------------------------------------------
# Force test environment before any app imports
# ---------------------------------------------------------------------------
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("APP_SECRET_KEY", "test-secret-key-at-least-32-chars-long-x")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key-at-least-32-chars-long-xx")
os.environ.setdefault("POSTGRES_USER", "saas_user")
os.environ.setdefault("POSTGRES_PASSWORD", "testpassword")
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_DB", "aivideosaas")
os.environ.setdefault("TEST_POSTGRES_DB", "aivideosaas_test")
os.environ.setdefault("REDIS_PASSWORD", "testredis")
os.environ.setdefault("CELERY_TASK_ALWAYS_EAGER", "true")
os.environ.setdefault("STORAGE_BACKEND", "local")
os.environ.setdefault("MEDIA_ROOT", "/tmp/test_media")
os.environ.setdefault("FIRST_SUPERUSER_PASSWORD", "Admin123!")

# ---------------------------------------------------------------------------
# App imports (after env vars are set)
# ---------------------------------------------------------------------------
from app.core.config import get_settings, settings
from app.core.security import create_access_token, hash_password
from app.db.base import Base
from app.db.session import build_test_engine, build_test_session_factory
from app.main import app
from backend.app.model.models_user import User, UserRole


# =============================================================================
# Event loop — single loop for the entire session
# =============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create a session-scoped event loop."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# =============================================================================
# Database — created once per session, tables wiped per test
# =============================================================================

@pytest.fixture(scope="session")
async def test_engine():
    """
    Create the test database engine once for the entire session.
    Tables are created on first use and dropped at session end.
    """
    engine = build_test_engine(str(settings.TEST_DATABASE_URL))

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture(scope="session")
def test_session_factory(test_engine):
    """Session-scoped async session factory bound to the test engine."""
    return build_test_session_factory(test_engine)


@pytest.fixture
async def db(test_session_factory: async_sessionmaker) -> AsyncGenerator[AsyncSession, None]:
    """
    Function-scoped database session.
    Each test runs inside a savepoint (nested transaction) that is rolled back
    at teardown — so tests never actually commit to the DB.
    """
    async with test_session_factory() as session:
        await session.begin_nested()   # SAVEPOINT
        try:
            yield session
        finally:
            await session.rollback()   # roll back to SAVEPOINT
            await session.close()


# =============================================================================
# FastAPI test client
# =============================================================================

@pytest.fixture
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Async HTTP test client with the DB session overridden.
    All requests go through the real FastAPI app with a test DB.
    """
    from app.db.session import get_db

    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# =============================================================================
# User fixtures
# =============================================================================

@pytest.fixture
async def test_user(db: AsyncSession) -> User:
    """Create and persist a regular test user."""
    user = User(
        email="testuser@example.com",
        hashed_password=hash_password("Testpass1!"),
        full_name="Test User",
        role=UserRole.USER,
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


@pytest.fixture
async def test_admin(db: AsyncSession) -> User:
    """Create and persist an admin test user."""
    user = User(
        email="admin@example.com",
        hashed_password=hash_password("Adminpass1!"),
        full_name="Admin User",
        role=UserRole.ADMIN,
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


@pytest.fixture
def user_token(test_user: User) -> str:
    """JWT access token for the test user."""
    return create_access_token(
        subject=test_user.id,
        extra_claims={"role": test_user.role, "email": test_user.email},
    )


@pytest.fixture
def admin_token(test_admin: User) -> str:
    """JWT access token for the admin user."""
    return create_access_token(
        subject=test_admin.id,
        extra_claims={"role": test_admin.role, "email": test_admin.email},
    )


@pytest.fixture
def auth_headers(user_token: str) -> dict[str, str]:
    """Authorization headers for the test user."""
    return {"Authorization": f"Bearer {user_token}"}


@pytest.fixture
def admin_headers(admin_token: str) -> dict[str, str]:
    """Authorization headers for the admin user."""
    return {"Authorization": f"Bearer {admin_token}"}


# =============================================================================
# Repository fixtures
# =============================================================================

@pytest.fixture
def user_repo(db: AsyncSession):
    from app.infrastructure.repositories.sqlalchemy_user_repository import (
        SQLAlchemyUserRepository,
    )
    return SQLAlchemyUserRepository(db)


@pytest.fixture
def project_repo(db: AsyncSession):
    from app.infrastructure.repositories.sqlalchemy_project_repository import (
        SQLAlchemyProjectRepository,
    )
    return SQLAlchemyProjectRepository(db)


@pytest.fixture
def video_repo(db: AsyncSession):
    from app.infrastructure.repositories.sqlalchemy_video_repository import (
        SQLAlchemyVideoRepository,
    )
    return SQLAlchemyVideoRepository(db)


@pytest.fixture
def task_repo(db: AsyncSession):
    from app.infrastructure.repositories.sqlalchemy_task_repository import (
        SQLAlchemyTaskRepository,
    )
    return SQLAlchemyTaskRepository(db)


# =============================================================================
# Service fixtures
# =============================================================================

@pytest.fixture
def auth_service(user_repo):
    from app.domain.services.auth_service import AuthService
    return AuthService(user_repo)


@pytest.fixture
def user_service(user_repo):
    from app.domain.services.user_service import UserService
    return UserService(user_repo)


@pytest.fixture
def project_service(project_repo):
    from app.domain.services.project_service import ProjectService
    return ProjectService(project_repo)


@pytest.fixture
def video_service(video_repo, project_repo):
    from app.domain.services.video_service import VideoService
    return VideoService(video_repo, project_repo)


@pytest.fixture
def task_service(task_repo, video_repo):
    from app.domain.services.task_service import TaskService
    return TaskService(task_repo, video_repo)


# =============================================================================
# Mock external services
# =============================================================================

@pytest.fixture
def mock_celery_task():
    """Mock Celery apply_async to prevent actual task dispatch in tests."""
    mock_result = MagicMock()
    mock_result.id = str(uuid4())
    with patch(
        "app.infrastructure.celery.tasks.video_tasks.process_video.apply_async",
        return_value=mock_result,
    ) as mock:
        yield mock


@pytest.fixture
def mock_ollama():
    """Mock OllamaClient.generate_script to return a fixed script."""
    with patch(
        "app.infrastructure.ai.ollama_client.OllamaClient.generate_script",
        new_callable=AsyncMock,
        return_value="This is a test generated script.",
    ) as mock:
        yield mock


@pytest.fixture
def mock_whisper():
    """Mock WhisperClient.transcribe to return fixed transcription."""
    with patch(
        "app.infrastructure.ai.whisper_client.WhisperClient.transcribe",
        new_callable=AsyncMock,
        return_value={
            "text": "This is a test transcription.",
            "language": "en",
            "language_probability": 0.99,
            "duration": 10.0,
            "segments": [
                {"id": 0, "start": 0.0, "end": 5.0, "text": "This is a test transcription."}
            ],
        },
    ) as mock:
        yield mock


@pytest.fixture
def mock_piper():
    """Mock PiperClient.synthesise to return a temp audio path."""
    import tempfile
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.write(b"RIFF" + b"\x00" * 36)   # minimal valid WAV header
    tmp.close()
    with patch(
        "app.infrastructure.ai.piper_client.PiperClient.synthesise",
        new_callable=AsyncMock,
        return_value=tmp.name,
    ) as mock:
        yield mock
    import os
    os.unlink(tmp.name)


@pytest.fixture
def mock_storage():
    """Mock FileStorage to avoid actual disk I/O in unit tests."""
    with patch(
        "app.infrastructure.storage.file_storage.FileStorage.upload",
        new_callable=AsyncMock,
        return_value="uploads/test/mock_file.mp4",
    ), patch(
        "app.infrastructure.storage.file_storage.FileStorage.upload_from_path",
        new_callable=AsyncMock,
        return_value="processed/test/mock_output.mp4",
    ), patch(
        "app.infrastructure.storage.file_storage.FileStorage.download_to_temp",
        new_callable=AsyncMock,
        return_value="/tmp/mock_download.mp4",
    ):
        yield