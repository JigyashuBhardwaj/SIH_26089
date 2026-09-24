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

Per the locked Phase 5C spec, this table deliberately did NOT include
leave/availability/workload fields — those are time-varying,
matching-adjacent, and remain deferred to a later phase.

Phase 5E-G adds the four profile/matching-data fields the future
matching phase needs as authoritative backend data (`address`,
`pincode`, `rating`, `total_jobs_completed`) — see each column's own
comment below for its exact constraints. No matching/ranking logic uses
these yet; this phase only establishes the data.

`status` (WorkerStatus: ACTIVE/INACTIVE, locked Phase 5C value list) is
the coarse worker account state, distinct from the deferred, leave-derived
availability. See `app/models/enums.py::WorkerStatus`.
"""

import uuid
from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import WorkerStatus
from app.models.mixins import TimestampMixin
from app.models.type_decorators import str_enum_column

# Deterministic placeholder values used both by the Phase 5E-G migration's
# existing-row backfill and here as this model's own Python-side defaults
# for any row created without explicitly supplying these fields (there is
# still no worker-creation endpoint in this phase — these only matter for
# direct ORM/test use). Not a database-level server_default: the DB never
# silently supplies these values on its own, per the project's
# "no hidden database state" rule.
DEFAULT_WORKER_ADDRESS = "Not Provided"
DEFAULT_WORKER_PINCODE = "000000"
DEFAULT_WORKER_RATING = Decimal("0.00")
DEFAULT_WORKER_TOTAL_JOBS_COMPLETED = 0


class Worker(TimestampMixin, Base):
    __tablename__ = "workers"
    __table_args__ = (
        Index("ix_workers_association_id", "association_id"),
        CheckConstraint("pincode ~ '^[0-9]{6}$'", name="ck_workers_pincode_six_digits"),
        CheckConstraint("rating >= 0 AND rating <= 5", name="ck_workers_rating_range"),
        CheckConstraint(
            "total_jobs_completed >= 0", name="ck_workers_total_jobs_completed_non_negative"
        ),
    )

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
    # The worker's service/location address. Required text; no structured
    # geocoding here (that belongs to a later matching phase).
    address: Mapped[str] = mapped_column(
        String(500), nullable=False, default=DEFAULT_WORKER_ADDRESS
    )
    # Exactly six digits, stored as text (never as an integer, which would
    # lose leading zeros) -- enforced both by column length and by the
    # `ck_workers_pincode_six_digits` CHECK constraint above.
    pincode: Mapped[str] = mapped_column(
        String(6), nullable=False, default=DEFAULT_WORKER_PINCODE
    )
    # 0.00-5.00 inclusive, enforced by `ck_workers_rating_range` above.
    # NUMERIC (not FLOAT) per the project's existing convention of exact
    # decimal types for anything that isn't a coordinate/measurement.
    rating: Mapped[Decimal] = mapped_column(
        Numeric(3, 2), nullable=False, default=DEFAULT_WORKER_RATING
    )
    # >= 0, enforced by `ck_workers_total_jobs_completed_non_negative`
    # above. Purely a running count maintained by a later phase (nothing
    # in the current, locked lifecycle increments this yet).
    total_jobs_completed: Mapped[int] = mapped_column(
        Integer, nullable=False, default=DEFAULT_WORKER_TOTAL_JOBS_COMPLETED
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
