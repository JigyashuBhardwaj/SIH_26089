"""
Domain model package.

Importing this package registers every table against the shared
`app.database.Base` metadata, which is what both Alembic's autogenerate
support (`alembic/env.py`) and `Base.metadata.create_all(...)` rely on.

No business logic, no API routes, no authentication lives here — this
package only defines the database schema (tables, columns, relationships,
constraints) for the nine core entities locked for Phase 5C:

Federation, Association, Account, UserProfile, Worker, Service,
WorkerSkill, ServiceRequest, Assignment.

Phase 7C-B adds a tenth: WorkerLeave (plus its LeaveStatus enum) — the
structural database foundation for worker leave. See
`app.models.worker_leave` for what this phase does and deliberately does
not implement yet.
"""

from app.models.account import Account
from app.models.assignment import Assignment
from app.models.association import Association
from app.models.enums import AccountRole, AssignmentStatus, ServiceRequestStatus, WorkerStatus
from app.models.federation import Federation
from app.models.service import Service
from app.models.service_request import ServiceRequest
from app.models.user_profile import UserProfile
from app.models.worker import Worker
from app.models.worker_leave import LeaveStatus, WorkerLeave
from app.models.worker_skill import WorkerSkill

__all__ = [
    "Account",
    "AccountRole",
    "Assignment",
    "AssignmentStatus",
    "Association",
    "Federation",
    "LeaveStatus",
    "Service",
    "ServiceRequest",
    "ServiceRequestStatus",
    "UserProfile",
    "Worker",
    "WorkerLeave",
    "WorkerSkill",
    "WorkerStatus",
]
