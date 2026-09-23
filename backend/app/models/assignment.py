"""
Assignment — one worker-offer attempt against a ServiceRequest. A request
accumulates MANY Assignment rows over its lifetime and none are ever
overwritten or deleted — e.g.:

    REQ-001
    Assignment #1 -> Mukesh   -> DECLINED
    Assignment #2 -> Worker B -> CANCELLED_BY_WORKER
    Assignment #3 -> Worker C -> ACCEPTED

That history requirement is exactly why there is NO unique constraint on
(request_id, worker_id): the same worker could legitimately be offered
the same request again later (re-offered after some other worker
cancelled, for instance), and a uniqueness constraint would forbid that.

`assigned_by` is a foreign key to `accounts.id` (ON DELETE RESTRICT) —
locked Phase 5C decision. Account is the one login-identity table in this
schema, and an assignment is always made by *someone* logged in (an
association admin today; conceivably an automated "system" account once
matching exists).

Fields follow the locked list exactly: id, request_id, worker_id,
assigned_by, status, assigned_at, responded_at. `assigned_at` serves as
this row's creation timestamp (there is no separate `created_at` here,
since the locked field list did not include one); `updated_at` is still
included so a later status change is reflected consistently with every
other table's timestamp strategy.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import AssignmentStatus
from app.models.type_decorators import str_enum_column


class Assignment(Base):
    __tablename__ = "assignments"
    __table_args__ = (
        Index("ix_assignments_request_id", "request_id"),
        Index("ix_assignments_worker_id_status", "worker_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("service_requests.id", ondelete="RESTRICT"),
        nullable=False,
    )
    worker_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workers.id", ondelete="RESTRICT"), nullable=False
    )
    assigned_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[AssignmentStatus] = mapped_column(
        str_enum_column(AssignmentStatus, name="assignment_status"),
        nullable=False,
        default=AssignmentStatus.PENDING_RESPONSE,
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    responded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    request: Mapped["ServiceRequest"] = relationship(back_populates="assignments")  # noqa: F821
    worker: Mapped["Worker"] = relationship(back_populates="assignments")  # noqa: F821
    assigned_by_account: Mapped["Account"] = relationship()  # noqa: F821
