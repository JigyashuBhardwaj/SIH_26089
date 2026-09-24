"""
FastAPI application entry point.

This is the startup/wiring layer only: it creates the app, configures
CORS for the existing mobile/admin dev clients, mounts the Phase 5D auth
router, the Phase 5E-B read-only service/user routers, and the Phase 5E-C
USER-owned ServiceRequest routes, and exposes a basic health check. No
worker/association/federation business routes, request lifecycle,
matching, or assignment are registered here yet — those arrive in later
phases.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.requests import router as requests_router
from app.api.services import router as services_router
from app.api.users import router as users_router
from app.config import get_settings

settings = get_settings()

app = FastAPI(
    title="Karmanya API",
    version="0.1.0",
    description=(
        "Karmanya backend. Phase 5D: authentication (/auth/login, "
        "/auth/me). Phase 5E-B: read-only service catalogue "
        "(/services, /services/{service_id}) and the authenticated "
        "user's own profile (/users/me). Phase 5E-C: the authenticated "
        "USER's own ServiceRequests (/requests, /requests/{request_id}) "
        "— creation only, always starting at PENDING; no matching, "
        "assignment, or lifecycle transitions yet."
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
app.include_router(services_router)
app.include_router(users_router)
app.include_router(requests_router)


@app.get("/health")
def health() -> dict[str, str]:
    """
    Basic liveness check. Deliberately does not touch the database — this
    only confirms the application process itself is up and configured.
    """
    return {"status": "ok", "environment": settings.app_env}
