"""
AirGuard AI — API entrypoint.

Boots the FastAPI application, wires middleware, mounts the versioned API
router, and ensures a first superuser account exists on startup.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.db.session import SessionLocal
from app.models.enums import UserRole
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate


def _ensure_first_superuser() -> None:
    db = SessionLocal()
    try:
        repo = UserRepository(db)
        existing = repo.get_by_email(settings.FIRST_SUPERUSER_EMAIL)
        if existing:
            return
        user = repo.create(
            UserCreate(
                full_name="System Administrator",
                email=settings.FIRST_SUPERUSER_EMAIL,
                password=settings.FIRST_SUPERUSER_PASSWORD,
                role=UserRole.ADMIN,
            )
        )
        user.is_superuser = True
        db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    _ensure_first_superuser()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description="AI-Powered Smart Industrial Parking & Environmental Safety Platform",
        version="0.1.0",
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        docs_url=f"{settings.API_V1_STR}/docs",
        redoc_url=f"{settings.API_V1_STR}/redoc",
        lifespan=lifespan,
    )

    if settings.BACKEND_CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.BACKEND_CORS_ORIGINS,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    app.include_router(api_router, prefix=settings.API_V1_STR)

    return app


app = create_app()
