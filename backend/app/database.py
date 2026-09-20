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
    FastAPI dependency that yields a request-scoped SQLAlchemy session
    and guarantees it's closed afterward. Future domain routes are
    expected to depend on this (`db: Session = Depends(get_db)`); no
    route currently uses it, since no domain models exist yet.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
