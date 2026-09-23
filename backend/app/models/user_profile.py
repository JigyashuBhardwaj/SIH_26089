"""
UserProfile — the profile data for an Account with role USER. 1:1 with
Account (`account_id` is UNIQUE); deleting the owning Account cascades to
its UserProfile (ON DELETE CASCADE), since a profile has no independent
existence without its login identity.
"""

import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import TimestampMixin


class UserProfile(TimestampMixin, Base):
    __tablename__ = "user_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)

    account: Mapped["Account"] = relationship(back_populates="user_profile")  # noqa: F821
    # passive_deletes=True: ServiceRequest.user_id is ON DELETE RESTRICT —
    # let PostgreSQL enforce that instead of SQLAlchemy nulling the FK.
    service_requests: Mapped[list["ServiceRequest"]] = relationship(  # noqa: F821
        back_populates="user", passive_deletes=True
    )
