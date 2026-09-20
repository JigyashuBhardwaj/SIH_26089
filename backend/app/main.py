"""
FastAPI application entry point.

This is the startup/wiring layer only: it creates the app, configures
CORS for the existing mobile/admin dev clients, and exposes a basic
health check. No domain routes, authentication, or business logic are
registered here yet — those arrive in later phases as their own routers.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings

settings = get_settings()

app = FastAPI(
    title="Karmanya API",
    version="0.1.0",
    description="Backend foundation for the Karmanya platform. No domain endpoints yet.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    """
    Basic liveness check. Deliberately does not touch the database — this
    only confirms the application process itself is up and configured.
    """
    return {"status": "ok", "environment": settings.app_env}
