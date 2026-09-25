"""
SQLAlchemy engine and session infrastructure.

This module establishes HOW the application talks to PostgreSQL. It
deliberately does not define any domain tables/models yet (no Federation,
Association, Account, User, Worker, Service, WorkerSkill, ServiceRequest,
or Assignment) — those belong to a later phase. `Base` is exported here
so that future model modules can import it and register their tables
against the same metadata, without this file needing to change.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

settings = get_settings()

# `pool_pre_ping` avoids handing out stale connections after the database
# has been idle/restarted — cheap insurance for a long-lived dev/demo
# backend. Engine creation itself does not open a connection; that only
# happens when a session is actually used (e.g. via `get_db` below), so
# the application can still start even if PostgreSQL isn't reachable yet.
engine = create_engine(settings.database_url, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Shared declarative base for future SQLAlchemy models."""


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields a request-scoped SQLAlchemy session and
    owns that request's whole transaction boundary — every route depends
    on this (`db: Session = Depends(get_db)`) rather than committing (or
    rolling back) for itself.

    Lifecycle:
      1. Open a new `Session` from `SessionLocal`.
      2. Yield it to the route handler.
      3. If the route returns normally (no exception propagated back into
         this generator), commit — this is the ONLY place any write this
         application makes is actually persisted. A route handler's own
         `db.add()`/`db.flush()`/`db.refresh()` calls remain exactly as
         they were: they stage/flush changes within this same transaction
         and let the handler read back server-generated values (ids,
         defaults, `request_code`, timestamps, ...), but none of that
         alone makes a write durable — only this commit does.
      4. If the route raises (a validation error, an `HTTPException` from
         `app/api/errors.py`, or anything else), roll back whatever was
         staged/flushed in this transaction and re-raise the original
         exception unchanged, so FastAPI's normal error handling/response
         still runs — this dependency never swallows or replaces an
         error, it only guarantees the transaction doesn't get committed
         first.
      5. Always close the session in `finally`, whichever path was taken,
         releasing its connection back to the pool.

    Before this, `get_db()` only closed the session in `finally` with no
    `commit()` anywhere in the codebase — every write was flushed and
    visible within its own request, then silently rolled back the moment
    that request's session closed, so it never actually reached the
    database for any later request to see (e.g. `POST /requests`
    appearing to succeed while a subsequent `GET /requests` found
    nothing). Centralizing the fix here, rather than adding `db.commit()`
    to every mutating route individually, fixes every current and future
    route at once and matches this function's existing role as the one
    place that owns session lifecycle.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
