# =============================================================================
# app/api/v1/router.py
# API v1 root router — mounts all endpoint sub-routers.
# =============================================================================
from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import auth, projects, tasks, users, videos

router = APIRouter()

router.include_router(auth.router,     prefix="/auth",     tags=["auth"])
router.include_router(users.router,    prefix="/users",    tags=["users"])
router.include_router(projects.router, prefix="/projects", tags=["projects"])
router.include_router(videos.router,   prefix="/videos",   tags=["videos"])
router.include_router(tasks.router,    prefix="/tasks",    tags=["tasks"])