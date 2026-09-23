"""
ServiceRequest — the central request entity, matching Phase 5A's shared
TypeScript model (`shared/types/booking.ts`) field-for-field. Deliberately
has NO `worker_id` column: which worker (if any) is currently tied to a
request is represented entirely through `Assignment` rows, never here.

`request_code` (e.g. "REQ-000123") is generated from a dedicated
PostgreSQL sequence (`request_code_seq`) via a server-side default
expression, so uniqueness and generation happen atomically in the
database rather than in application code with a race condition. Per the
locked spec this is NOT guaranteed gapless (a rolled-back INSERT still
consumes a sequence value) — only guaranteed unique.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Sequence, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import ServiceRequestStatus
from app.models.mixins import TimestampMixin
from app.models.type_decorators import str_enum_column

# Backs `request_code`'s server-side default below. Declared at module
# level (rather than inline) so Alembic's autogenerate can see it as its
# own DDL object and the initial migration can create it explicitly.
request_code_seq = Sequence("request_code_seq", start=1, metadata=Base.metadata)


class ServiceRequest(TimestampMixin, Base):
    __tablename__ = "service_requests"
    __table_args__ = (
        Index("ix_service_requests_status", "status"),
        Index("ix_service_requests_association_id_status", "association_id", "status"),
        Index("ix_service_requests_pincode", "pincode"),
        Index("ix_service_requests_user_id", "user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    request_code: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
        server_default=text(
            "'REQ-' || lpad(nextval('request_code_seq')::text, 6, '0')"
        ),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user_profiles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    service_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("services.id", ondelete="RESTRICT"), nullable=False
    )
    association_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("associations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[ServiceRequestStatus] = mapped_column(
        str_enum_column(ServiceRequestStatus, name="service_request_status"),
        nullable=False,
        default=ServiceRequestStatus.PENDING,
    )
    address: Mapped[str] = mapped_column(String(500), nullable=False)
    pincode: Mapped[str] = mapped_column(String(10), nullable=False)
    requested_date_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    user: Mapped["UserProfile"] = relationship(back_populates="service_requests")  # noqa: F821
    service: Mapped["Service"] = relationship(back_populates="service_requests")  # noqa: F821
    association: Mapped["Association"] = relationship(back_populates="service_requests")  # noqa: F821
    # passive_deletes=True: Assignment.request_id is ON DELETE RESTRICT —
    # let PostgreSQL enforce that instead of SQLAlchemy nulling the FK.
    assignments: Mapped[list["Assignment"]] = relationship(  # noqa: F821
        back_populates="request", passive_deletes=True
    )
