"""
Shared column mixins.

Per the locked Phase 5C timestamp strategy: TIMESTAMPTZ everywhere, every
model gets `created_at`/`updated_at`, `updated_at` refreshed via
SQLAlchemy's `onupdate` (application-side, on the Python `UPDATE`
statement it issues) rather than a PostgreSQL trigger — no DB triggers in
Phase 5C.
"""

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column


class TimestampMixin:
    """Adds `created_at`/`updated_at` TIMESTAMPTZ columns to a model."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
