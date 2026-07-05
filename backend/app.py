from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend import settings
from backend.api import (
    activity_router,
    chat_router,
    files_router,
    generate_router,
    projects_router,
    voices_manager_router,
    voices_router,
)


def create_app() -> FastAPI:
    app = FastAPI(title="Writer Content Production System")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(projects_router.router, prefix="/api")
    app.include_router(files_router.router, prefix="/api")
    app.include_router(voices_router.router, prefix="/api")
    app.include_router(chat_router.router, prefix="/api")
    app.include_router(generate_router.router, prefix="/api")
    app.include_router(activity_router.router, prefix="/api")
    app.include_router(voices_manager_router.router, prefix="/api")
    app.include_router(voices_manager_router.templates_router, prefix="/api")

    @app.on_event("startup")
    async def ensure_runtime_dirs() -> None:
        settings.PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
        settings.VOICES_DIR.mkdir(parents=True, exist_ok=True)

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
