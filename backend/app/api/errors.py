"""
Small, shared helpers for the error-status codes that don't already have
an established convention elsewhere in this codebase.

Deliberately NOT a custom exception framework — every route (present and
future) still raises a plain FastAPI `HTTPException` directly, exactly as
`app/auth/dependencies.py` and `app/auth/scope.py` already do. This module
exists only so future routes reach for the same 400/404/409 helper rather
than each hand-rolling its own `HTTPException(...)` call.

Status codes that already have an established, LOCKED convention and are
therefore NOT touched here:

- 401 Unauthorized — `app.auth.dependencies` (`get_current_account`).
  Preserves the generic, non-enumerating "Invalid login credentials" /
  "Not authenticated" / "Could not validate credentials" messages.
- 403 Forbidden — `app.auth.dependencies` (`require_role`) and
  `app.auth.scope` (the `ensure_*_scope` helpers).
- 422 Unprocessable Entity — raised automatically by FastAPI/Pydantic
  request validation; nothing to add here.
"""

from fastapi import HTTPException, status


def bad_request(detail: str = "Bad request") -> HTTPException:
    """400 — the request itself is malformed/invalid in a way validation didn't catch."""
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def not_found(detail: str = "Resource not found") -> HTTPException:
    """404 — the referenced resource doesn't exist (or isn't visible to this caller)."""
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def conflict(detail: str = "Conflict") -> HTTPException:
    """409 — the request conflicts with the resource's current state."""
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)
