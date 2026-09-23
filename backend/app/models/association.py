"""
Association — belongs to exactly one Federation; Workers belong to
exactly one Association.

`pincode_coverage` is explicitly deferred per the locked Phase 5C spec
(not modeled here at all, not even as a nullable column) — it belongs to
whatever later phase actually needs geographic coverage matching.
"""

import uuid

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import TimestampMixin


class Association(TimestampMixin, Base):
    __tablename__ = "associations"
    __table_args__ = (Index("ix_associations_federation_id", "federation_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    federation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("federations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    federation: Mapped["Federation"] = relationship(back_populates="associations")  # noqa: F821
    # passive_deletes=True on all three collections below: their FKs are
    # all ON DELETE RESTRICT, so PostgreSQL — not SQLAlchemy nulling the
    # FK client-side first — is what decides an Association delete is
    # blocked while any of these still reference it.
    workers: Mapped[list["Worker"]] = relationship(  # noqa: F821
        back_populates="association", passive_deletes=True
    )
    accounts: Mapped[list["Account"]] = relationship(  # noqa: F821
        back_populates="association", passive_deletes=True
    )
    service_requests: Mapped[list["ServiceRequest"]] = relationship(  # noqa: F821
        back_populates="association", passive_deletes=True
    )
