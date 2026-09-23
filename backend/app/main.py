"""
FastAPI application entry point.

This is the startup/wiring layer only: it creates the app, configures
CORS for the existing mobile/admin dev clients, mounts the Phase 5D auth
router, and exposes a basic health check. No business/domain routes are
registered here yet — those arrive in later phases as their own routers.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.config import get_settings

settings = get_settings()

app = FastAPI(
    title="Karmanya API",
    version="0.1.0",
    description=(
        "Karmanya backend. Phase 5D: authentication (/auth/login, /auth/me) "
        "only — no business/domain endpoints yet."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)


@app.get("/health")
def health() -> dict[str, str]:
    """
    Basic liveness check. Deliberately does not touch the database — this
    only confirms the application process itself is up and configured.
    """
    return {"status": "ok", "environment": settings.app_env}
