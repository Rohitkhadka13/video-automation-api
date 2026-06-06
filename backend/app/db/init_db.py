# =============================================================================
# app/db/init_db.py
# First-run database seed.
# Creates the initial superuser if no users exist.
# Called once from the app lifespan after migrations have run.
# =============================================================================
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import hash_password
from app.model.models_user import User, UserRole

logger = get_logger(__name__)


async def init_db(db: AsyncSession) -> None:
    """
    Seed the database with initial data on first run.

    This function is idempotent — running it multiple times is safe.
    It checks for the existence of the superuser before creating it.
    """
    await _create_first_superuser(db)


async def _create_first_superuser(db: AsyncSession) -> None:
    """Create the initial admin user if they don't already exist."""
    stmt = select(User).where(User.email == settings.FIRST_SUPERUSER_EMAIL)
    result = await db.execute(stmt)
    existing_user = result.scalar_one_or_none()

    if existing_user:
        logger.debug(
            "db.seed.superuser.already_exists",
            email=settings.FIRST_SUPERUSER_EMAIL,
        )
        return

    superuser = User(
        email=settings.FIRST_SUPERUSER_EMAIL,
        hashed_password=hash_password(settings.FIRST_SUPERUSER_PASSWORD),
        full_name=settings.FIRST_SUPERUSER_FULL_NAME,
        role=UserRole.ADMIN,
        is_active=True,
        is_verified=True,
    )
    db.add(superuser)
    await db.flush()

    logger.info(
        "db.seed.superuser.created",
        email=settings.FIRST_SUPERUSER_EMAIL,
        user_id=str(superuser.id),
    )