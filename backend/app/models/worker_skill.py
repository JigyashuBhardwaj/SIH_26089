"""
WorkerSkill — the many-to-many join between Worker and Service.
Composite primary key (worker_id, service_id) is itself the uniqueness
guarantee (a worker can't be skilled in the same service twice); both
foreign keys cascade on delete, since a join row has no meaning once
either side it links is gone.
"""

import uuid

from sqlalchemy import ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import TimestampMixin


class WorkerSkill(TimestampMixin, Base):
    __tablename__ = "worker_skills"
    __table_args__ = (Index("ix_worker_skills_service_id", "service_id"),)

    worker_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workers.id", ondelete="CASCADE"), primary_key=True
    )
    service_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("services.id", ondelete="CASCADE"), primary_key=True
    )

    worker: Mapped["Worker"] = relationship(back_populates="skills")  # noqa: F821
    service: Mapped["Service"] = relationship(back_populates="worker_skills")  # noqa: F821
