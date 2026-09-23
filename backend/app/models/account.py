"""
Account — the single login identity table for every role (USER, WORKER,
ASSOCIATION_ADMIN, FEDERATION_ADMIN). One Account per login; the actual
profile data for a person lives in a separate, role-specific table
(UserProfile, Worker) linked back to this Account.

Authentication itself (password hashing/verification, JWT issuance,
login endpoints) is explicitly out of scope for Phase 5C — `password_hash`
exists here purely as the column future auth work will populate, and is
nullable for now since nothing writes to it yet.

Role-scope invariants — e.g. "an ASSOCIATION_ADMIN account must have a
non-null association_id", "a FEDERATION_ADMIN account must have a
non-null federation_id" — are application-level rules for a later phase,
not enforced by a DB constraint here (no CHECK/trigger cross-validates
role against association_id/federation_id in Phase 5C).
"""

import uuid

from sqlalchemy import Boolean, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import AccountRole
from app.models.mixins import TimestampMixin
from app.models.type_decorators import str_enum_column


class Account(TimestampMixin, Base):
    __tablename__ = "accounts"
    __table_args__ = (
        Index("ix_accounts_role", "role"),
        Index("ix_accounts_association_id", "association_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    login_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    role: Mapped[AccountRole] = mapped_column(
        str_enum_column(AccountRole, name="account_role"), nullable=False
    )
    # Nullable in Phase 5C: no auth flow writes to this column yet.
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    association_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("associations.id", ondelete="RESTRICT"), nullable=True
    )
    federation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("federations.id", ondelete="RESTRICT"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    association: Mapped["Association | None"] = relationship(back_populates="accounts")  # noqa: F821
    federation: Mapped["Federation | None"] = relationship()  # noqa: F821
    # passive_deletes=True: UserProfile.account_id is ON DELETE CASCADE and
    # Worker.account_id is ON DELETE RESTRICT — both should be enforced by
    # PostgreSQL itself, not by SQLAlchemy trying to null the FK first.
    user_profile: Mapped["UserProfile | None"] = relationship(  # noqa: F821
        back_populates="account", uselist=False, passive_deletes=True
    )
    worker: Mapped["Worker | None"] = relationship(  # noqa: F821
        back_populates="account", uselist=False, passive_deletes=True
    )
