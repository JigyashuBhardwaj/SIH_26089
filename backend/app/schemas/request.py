"""
Typed request/response models for the Phase 5E-C `ServiceRequest` routes.

Deliberately separate from `app.models.service_request.ServiceRequest`
(the SQLAlchemy model) — no route ever returns that model directly, and
`ServiceRequestCreate` only accepts exactly the fields a client is
allowed to set. Everything else (`id`, `request_code`, `user_id`,
`status`, `created_at`, `updated_at`) is owned by the server.
"""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import ServiceRequestStatus

# Locked product requirement: a requested service time must be at least
# this far in the future, relative to server time at creation.
MINIMUM_LEAD_TIME = timedelta(hours=4)


class ServiceRequestCreate(BaseModel):
    """
    `POST /requests` request body. Only the fields a client may supply —
    `user_id`/`request_code`/`status`/`worker_id`/`assignment_id`/
    `created_at`/`updated_at` are never accepted here; the server always
    computes them.
    """

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    service_id: UUID = Field(alias="serviceId")
    association_id: UUID = Field(alias="associationId")
    requested_date_time: datetime = Field(alias="requestedDateTime")
    address: str = Field(min_length=1, max_length=500)
    pincode: str = Field(min_length=1, max_length=10)

    @field_validator("requested_date_time")
    @classmethod
    def _validate_requested_date_time(cls, value: datetime) -> datetime:
        """
        Reject a naive datetime outright (rather than silently guessing a
        timezone, which would create ambiguity), and reject any
        timezone-aware datetime less than `MINIMUM_LEAD_TIME` from the
        current server time.
        """
        if value.tzinfo is None:
            raise ValueError(
                "requestedDateTime must be a timezone-aware ISO-8601 datetime "
                "(e.g. include a UTC offset or 'Z')"
            )

        now = datetime.now(timezone.utc)
        if value < now + MINIMUM_LEAD_TIME:
            raise ValueError(
                "requestedDateTime must be at least 4 hours from the current time"
            )

        return value


class ServiceRequestPublic(BaseModel):
    """
    Safe, public view of a `ServiceRequest`. Never includes `user_id`,
    worker/assignment information, or any authentication data.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    request_code: str = Field(alias="requestCode")
    service_id: UUID = Field(alias="serviceId")
    association_id: UUID = Field(alias="associationId")
    requested_date_time: datetime = Field(alias="requestedDateTime")
    address: str
    pincode: str
    status: ServiceRequestStatus
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


class ServiceRequestListResponse(BaseModel):
    """Paginated envelope for `GET /requests`."""

    model_config = ConfigDict(populate_by_name=True)

    items: list[ServiceRequestPublic]
    page: int
    page_size: int = Field(alias="pageSize")
    total: int
