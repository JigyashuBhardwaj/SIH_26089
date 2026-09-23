"""
Service — the catalogue entry a Worker can be skilled in and a
ServiceRequest can be raised against (e.g. "Plumber", "Electrician"),
mirroring the existing mobile service catalogue's concept.
"""

import uuid

from sqlalchemy import Boolean, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import TimestampMixin


class Service(TimestampMixin, Base):
    __tablename__ = "services"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # passive_deletes=True: WorkerSkill.service_id is ON DELETE CASCADE and
    # ServiceRequest.service_id is ON DELETE RESTRICT — both belong to
    # PostgreSQL to enforce, not SQLAlchemy nulling the FK client-side.
    worker_skills: Mapped[list["WorkerSkill"]] = relationship(  # noqa: F821
        back_populates="service", passive_deletes=True
    )
    service_requests: Mapped[list["ServiceRequest"]] = relationship(  # noqa: F821
        back_populates="service", passive_deletes=True
    )
