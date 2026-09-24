"""
Shared pytest fixtures for the backend test suite.

CRITICAL SAFETY RULE (Phase 5E-A locked requirement): this test suite must
NEVER connect to the real development database (`karmanya`). To guarantee
that "by construction" rather than by convention:

1. `TEST_DATABASE_URL` must be set in the environment before running
   pytest. There is no fallback/default — if it's missing, we fail loudly
   here, at collection time, before any test (or any `app.*` module) runs.
2. We override `os.environ["DATABASE_URL"]` to `TEST_DATABASE_URL` at the
   very top of this file, BEFORE importing anything from `app.*`. This
   matters because `app/database.py` creates its SQLAlchemy `engine` at
   *import* time, from a module-level `get_settings()` call — if we only
   used FastAPI's `dependency_overrides` mechanism, that module-level
   engine would still silently point at the dev database, and anything
   that used it directly (rather than through `Depends(get_db)`) would
   touch real data.
3. We refuse to proceed if `TEST_DATABASE_URL` happens to equal whatever
   the development `DATABASE_URL` resolves to (from an already-exported
   env var, or from `backend/.env`), as a last-resort guard against a
   misconfigured environment.

See `backend/README.md` for how to create the isolated test database this
suite expects.
"""

import os
import sys
import uuid
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
if not TEST_DATABASE_URL:
    raise RuntimeError(
        "TEST_DATABASE_URL is not set. Refusing to run this test suite "
        "without an explicit, isolated test database — it must never run "
        "against the real development database ('karmanya'). Set "
        "TEST_DATABASE_URL to a dedicated PostgreSQL database before "
        "running pytest. See backend/README.md for setup instructions."
    )

# Figure out what the *development* DATABASE_URL would resolve to, without
# importing any `app.*` module yet — first an already-exported env var,
# then a plain-text scan of backend/.env (mirroring how pydantic-settings
# would load it), so we can refuse if it's identical to the test URL.
_dev_database_url = os.environ.get("DATABASE_URL")
_dotenv_path = BACKEND_DIR / ".env"
if _dotenv_path.exists():
    for _line in _dotenv_path.read_text().splitlines():
        _line = _line.strip()
        if _line.startswith("DATABASE_URL=") and not _line.startswith("#"):
            _dev_database_url = _line.split("=", 1)[1].strip()

if _dev_database_url and _dev_database_url == TEST_DATABASE_URL:
    raise RuntimeError(
        "TEST_DATABASE_URL is identical to the development DATABASE_URL. "
        "Refusing to run tests against the real development database."
    )

# Force every `app.*` module (including pydantic-settings' own .env
# loading) to see the test database URL from this point on.
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.auth.security import create_access_token, hash_password  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.database import Base, engine, get_db  # noqa: E402
from app.main import app  # noqa: E402
from datetime import datetime, timedelta, timezone  # noqa: E402

from app.models import (  # noqa: E402
    Account,
    AccountRole,
    Assignment,
    AssignmentStatus,
    Association,
    Federation,
    Service,
    ServiceRequest,
    ServiceRequestStatus,
    UserProfile,
    Worker,
    WorkerSkill,
    WorkerStatus,
)

# Belt-and-suspenders: confirm the application actually resolved the test
# database URL, not something else picked up from the environment.
assert get_settings().database_url == TEST_DATABASE_URL, (
    "app settings resolved a DATABASE_URL different from TEST_DATABASE_URL "
    "— refusing to proceed."
)


@pytest.fixture(scope="session", autouse=True)
def _test_schema():
    """
    Create the domain schema once for the whole test run, using the
    existing SQLAlchemy models directly (`Base.metadata.create_all`) —
    deliberately NOT via Alembic, so the test suite's schema setup stays
    fully decoupled from the production migration tooling. Torn down at
    the end of the run.
    """
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db_session():
    """
    A SQLAlchemy session bound to a single connection wrapped in an outer
    transaction that is always rolled back at the end of the test — so
    every test starts from a clean slate and no test's data leaks into
    another's, without needing per-test create/drop of the whole schema.
    """
    connection = engine.connect()
    transaction = connection.begin()
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=connection)
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture()
def client(db_session):
    """
    A FastAPI `TestClient` whose `get_db` dependency is overridden to
    yield the SAME session object as `db_session` — so data a test
    fixture creates (via `db_session.flush()`) is visible to the
    application's own queries within that request, without needing a
    commit that would break the rollback-based isolation above.
    """

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture()
def make_account(db_session):
    """Factory fixture: create a temporary `Account` row for this test."""

    def _make_account(
        *,
        login_id: str | None = None,
        password: str | None = None,
        role: AccountRole = AccountRole.USER,
        is_active: bool = True,
        association_id=None,
        federation_id=None,
    ) -> Account:
        account = Account(
            login_id=login_id or f"test_{uuid.uuid4().hex[:12]}",
            role=role,
            password_hash=hash_password(password) if password is not None else None,
            is_active=is_active,
            association_id=association_id,
            federation_id=federation_id,
        )
        db_session.add(account)
        db_session.flush()
        db_session.refresh(account)
        return account

    return _make_account


@pytest.fixture()
def make_federation(db_session):
    """Factory fixture: create a temporary `Federation` row for this test."""

    def _make_federation(*, name: str | None = None) -> Federation:
        federation = Federation(name=name or f"Federation {uuid.uuid4().hex[:8]}")
        db_session.add(federation)
        db_session.flush()
        db_session.refresh(federation)
        return federation

    return _make_federation


@pytest.fixture()
def make_association(db_session):
    """Factory fixture: create a temporary `Association` row for this test."""

    def _make_association(*, federation_id, name: str | None = None) -> Association:
        association = Association(
            federation_id=federation_id,
            name=name or f"Association {uuid.uuid4().hex[:8]}",
        )
        db_session.add(association)
        db_session.flush()
        db_session.refresh(association)
        return association

    return _make_association


@pytest.fixture()
def make_worker(db_session):
    """Factory fixture: create a temporary `Worker` row for this test."""

    def _make_worker(
        *,
        account_id,
        association_id,
        worker_code: str | None = None,
        full_name: str = "Test Worker",
    ) -> Worker:
        worker = Worker(
            account_id=account_id,
            association_id=association_id,
            worker_code=worker_code or f"TW-{uuid.uuid4().hex[:8]}",
            full_name=full_name,
            status=WorkerStatus.ACTIVE,
        )
        db_session.add(worker)
        db_session.flush()
        db_session.refresh(worker)
        return worker

    return _make_worker


@pytest.fixture()
def make_worker_skill(db_session):
    """Factory fixture: link a `Worker` to a `Service` via `WorkerSkill` (Phase 5E-E)."""

    def _make_worker_skill(*, worker_id, service_id) -> WorkerSkill:
        worker_skill = WorkerSkill(worker_id=worker_id, service_id=service_id)
        db_session.add(worker_skill)
        db_session.flush()
        db_session.refresh(worker_skill)
        return worker_skill

    return _make_worker_skill


@pytest.fixture()
def make_service(db_session):
    """Factory fixture: create a temporary `Service` row for this test (Phase 5E-B)."""

    def _make_service(
        *,
        name: str | None = None,
        category: str = "General",
        is_active: bool = True,
    ) -> Service:
        service = Service(
            name=name or f"Service {uuid.uuid4().hex[:8]}",
            category=category,
            is_active=is_active,
        )
        db_session.add(service)
        db_session.flush()
        db_session.refresh(service)
        return service

    return _make_service


@pytest.fixture()
def make_user_profile(db_session):
    """Factory fixture: create a temporary `UserProfile` row for this test (Phase 5E-B)."""

    def _make_user_profile(
        *,
        account_id,
        full_name: str = "Test User",
        phone: str | None = "9876543210",
    ) -> UserProfile:
        profile = UserProfile(account_id=account_id, full_name=full_name, phone=phone)
        db_session.add(profile)
        db_session.flush()
        db_session.refresh(profile)
        return profile

    return _make_user_profile


@pytest.fixture()
def make_service_request(db_session):
    """
    Factory fixture: create a temporary `ServiceRequest` row directly
    (Phase 5E-D). Constructs the ORM row directly rather than going
    through `POST /requests`, so it deliberately bypasses that endpoint's
    own lead-time validation — callers can pass any `requested_date_time`
    they need for ordering/isolation tests.
    """

    def _make_service_request(
        *,
        user_id,
        service_id,
        association_id,
        requested_date_time: datetime | None = None,
        address: str = "12 MG Road",
        pincode: str = "560001",
        status: ServiceRequestStatus = ServiceRequestStatus.PENDING,
    ) -> ServiceRequest:
        service_request = ServiceRequest(
            user_id=user_id,
            service_id=service_id,
            association_id=association_id,
            requested_date_time=requested_date_time
            or (datetime.now(timezone.utc) + timedelta(hours=5)),
            address=address,
            pincode=pincode,
            status=status,
        )
        db_session.add(service_request)
        db_session.flush()
        db_session.refresh(service_request)
        return service_request

    return _make_service_request


@pytest.fixture()
def make_assignment(db_session):
    """Factory fixture: create a temporary `Assignment` row for this test (Phase 5E-D)."""

    def _make_assignment(
        *,
        request_id,
        worker_id,
        assigned_by,
        status: AssignmentStatus = AssignmentStatus.PENDING_RESPONSE,
    ) -> Assignment:
        assignment = Assignment(
            request_id=request_id,
            worker_id=worker_id,
            assigned_by=assigned_by,
            status=status,
        )
        db_session.add(assignment)
        db_session.flush()
        db_session.refresh(assignment)
        return assignment

    return _make_assignment


@pytest.fixture()
def auth_header():
    """Factory fixture: build an `Authorization: Bearer <token>` header for an Account."""

    def _auth_header(account: Account) -> dict[str, str]:
        token = create_access_token(account_id=account.id, role=account.role)
        return {"Authorization": f"Bearer {token}"}

    return _auth_header
