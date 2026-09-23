"""
Status/role enum definitions shared by the domain models.

Per the locked Phase 5C decision, every enum here is a plain Python
`enum.Enum` (str-valued) persisted as VARCHAR + CHECK constraint via
`sqlalchemy.Enum(..., native_enum=False, ...)` in the model columns that
use them — never a native PostgreSQL ENUM type (`CREATE TYPE ... AS ENUM`),
since those are painful to alter later (Postgres historically required
dropping/recreating the type, or restrictive ALTER TYPE rules, to add or
remove a value).
"""

from enum import Enum


class AccountRole(str, Enum):
    """Role of the single login identity represented by an Account row."""

    USER = "USER"
    WORKER = "WORKER"
    ASSOCIATION_ADMIN = "ASSOCIATION_ADMIN"
    FEDERATION_ADMIN = "FEDERATION_ADMIN"


class WorkerStatus(str, Enum):
    """
    Coarse account-level status of a Worker row — locked Phase 5C value
    list: ACTIVE, INACTIVE. Distinct from the *computed*, leave-derived
    "Available"/"Unavailable" availability, which Phase 5C explicitly
    defers along with the rest of Worker's leave/availability/workload/
    matching-score fields (matching-adjacent derived/time-based state
    belonging to a later phase).
    """

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class ServiceRequestStatus(str, Enum):
    """
    Request-level status, identical to the Phase 5A shared TypeScript
    `ServiceRequestStatus` union (`shared/types/booking.ts`). Deliberately
    excludes IN_PROGRESS, DECLINED, REASSIGNING, and CANCELLED_BY_WORKER —
    those never existed at the request level; DECLINED/CANCELLED_BY_WORKER
    are Assignment-level only (see AssignmentStatus below).
    """

    PENDING = "PENDING"
    MATCHING = "MATCHING"
    ASSIGNED = "ASSIGNED"
    ACCEPTED = "ACCEPTED"
    WORKER_COMPLETED = "WORKER_COMPLETED"
    USER_CONFIRMED = "USER_CONFIRMED"
    PAYMENT_PENDING = "PAYMENT_PENDING"
    PAID = "PAID"
    COMPLETED = "COMPLETED"
    CANCELLED_BY_USER = "CANCELLED_BY_USER"


class AssignmentStatus(str, Enum):
    """
    Per-assignment-attempt status. Separate from ServiceRequestStatus:
    a single ServiceRequest can accumulate several Assignment rows over
    its lifetime (one worker declines, another is offered next, etc.),
    and none of them are ever overwritten — see `Assignment`'s docstring.
    """

    PENDING_RESPONSE = "PENDING_RESPONSE"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"
    CANCELLED_BY_WORKER = "CANCELLED_BY_WORKER"
    COMPLETED = "COMPLETED"
