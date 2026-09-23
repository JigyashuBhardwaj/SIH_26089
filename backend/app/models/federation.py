"""
Federation — the top level of the locked Federation -> Association ->
Worker hierarchy.

This is a Karmanya product architecture/model, not a claim about the
real-world legal structure of Indian labour organizations. Multiple
Federation rows must be schema-legal (no hardcoded singleton row/id) —
there is nothing here that assumes only one Federation will ever exist.
"""

import uuid

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import TimestampMixin


class Federation(TimestampMixin, Base):
    __tablename__ = "federations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # passive_deletes=True: let PostgreSQL's own ON DELETE RESTRICT (set on
    # Association.federation_id) decide what happens on a Federation
    # delete, instead of SQLAlchemy's default behavior of first trying to
    # UPDATE each child's FK to NULL in Python (which would itself fail
    # here, since federation_id is NOT NULL, masking the real constraint).
    associations: Mapped[list["Association"]] = relationship(  # noqa: F821
        back_populates="federation", passive_deletes=True
    )
