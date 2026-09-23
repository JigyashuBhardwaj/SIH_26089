"""
Worker — the profile data for an Account with role WORKER. 1:1 with
Account (`account_id` UNIQUE, ON DELETE RESTRICT — deleting a Worker's
underlying Account while a Worker row references it is blocked rather
than silently cascading, since a Worker can carry assignment history
that must never be orphaned by a login-identity deletion).

Belongs to exactly one Association (ON DELETE RESTRICT — an Association
can't be deleted out from under workers that still reference it).

`worker_code` is the human-readable identifier (e.g. "SKW-0066") kept
separate from the UUID primary key, per the locked "human-readable IDs
separate from DB UUIDs" decision; nothing generates these yet in Phase
5C since no workers are created here (see the "no seed/demo data" rule).

Per the locked spec, this table deliberately does NOT include
leave/availability/workload/matching-score fields — those are
time-varying, matching-adjacent, and deferred to a later phase.

`status` (WorkerStatus: ACTIVE/INACTIVE, locked Phase 5C value list) is
the coarse worker account state, distinct from the deferred, leave-derived
availability. See `app/models/enums.py::WorkerStatus`.
"""

import uuid

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import WorkerStatus
from app.models.mixins import TimestampMixin
from app.models.type_decorators import str_enum_column


class Worker(TimestampMixin, Base):
    __tablename__ = "workers"
    __table_args__ = (Index("ix_workers_association_id", "association_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        unique=True,
        nullable=False,
    )
    association_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("associations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    worker_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[WorkerStatus] = mapped_column(
        str_enum_column(WorkerStatus, name="worker_status"),
        nullable=False,
        default=WorkerStatus.ACTIVE,
    )

    account: Mapped["Account"] = relationship(back_populates="worker")  # noqa: F821
    association: Mapped["Association"] = relationship(back_populates="workers")  # noqa: F821
    # passive_deletes=True: WorkerSkill.worker_id is ON DELETE CASCADE and
    # Assignment.worker_id is ON DELETE RESTRICT — both belong to
    # PostgreSQL to enforce, not SQLAlchemy nulling the FK client-side.
    skills: Mapped[list["WorkerSkill"]] = relationship(  # noqa: F821
        back_populates="worker", passive_deletes=True
    )
    assignments: Mapped[list["Assignment"]] = relationship(  # noqa: F821
        back_populates="worker", passive_deletes=True
    )
