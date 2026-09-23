# backend/

The single central backend/API that `mobile/` and `admin/` both talk to.
Owns the database and is the authoritative enforcer of request state and
authorization (client-side copies of any rule are for UI responsiveness
only, never the security/consistency boundary).

Stack: **Python, FastAPI, SQLAlchemy, PostgreSQL** — see
`KARMANYA_BACKEND_ARCHITECTURE.md` for the full architecture this backend
is being built against.

## Status: Phase 5E-A — API/Testing Foundation

Phase 5B (application skeleton), Phase 5C (domain database schema, nine
tables), and Phase 5D (authentication + authorization) are done and
functionally unchanged. Phase 5E-A adds the **foundation** future domain
APIs will build on — organization for future routers, shared Pydantic
schema/error/pagination conventions, and a permanent, isolated automated
test suite that converts the earlier Phase 5D manual verification into
repeatable pytest tests. **No business/domain endpoints, no schema
changes, no seed/demo data** — see "Testing" below.

`POST /auth/login`, `GET /auth/me`, JWT issuance/verification, and the
reusable auth dependencies described below are unchanged from Phase 5D.

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py               # FastAPI app, CORS, GET /health, mounts auth router
│   ├── config.py              # Settings: DB, CORS, + Phase 5D JWT config
│   ├── database.py            # SQLAlchemy engine/session, Base
│   ├── models/                 # Phase 5C: domain schema only, no routes/business logic
│   │   ├── __init__.py         # imports every model so Base.metadata sees all 9 tables
│   │   ├── enums.py            # AccountRole, WorkerStatus, ServiceRequestStatus, AssignmentStatus
│   │   ├── mixins.py           # TimestampMixin (created_at/updated_at)
│   │   ├── type_decorators.py  # str_enum_column(): VARCHAR+CHECK, not a native PG enum
│   │   ├── federation.py
│   │   ├── association.py
│   │   ├── account.py
│   │   ├── user_profile.py
│   │   ├── worker.py
│   │   ├── service.py
│   │   ├── worker_skill.py
│   │   ├── service_request.py
│   │   └── assignment.py
│   ├── auth/                   # Phase 5D: password hashing, JWT, auth dependencies
│   │   ├── __init__.py
│   │   ├── security.py         # hash_password/verify_password (Argon2id), create/decode_access_token (JWT)
│   │   ├── dependencies.py     # get_current_account, require_role — reusable, not duplicated per-route
│   │   └── scope.py            # organization-scope foundations for future routes (see below)
│   ├── schemas/                 # typed request/response models
│   │   ├── __init__.py
│   │   ├── auth.py             # Phase 5D: LoginRequest, AccountPublic (never password_hash), LoginResponse
│   │   └── pagination.py       # Phase 5E-A: PaginationParams/PaginatedResponse foundation (unwired)
│   └── api/                     # routers
│       ├── __init__.py
│       ├── auth.py             # Phase 5D: POST /auth/login, GET /auth/me
│       ├── errors.py           # Phase 5E-A: shared 400/404/409 helpers (unwired)
│       ├── users.py            # Phase 5E-A: placeholder router, no endpoints, not mounted
│       ├── workers.py          # Phase 5E-A: placeholder router, no endpoints, not mounted
│       ├── associations.py     # Phase 5E-A: placeholder router, no endpoints, not mounted
│       ├── federation.py       # Phase 5E-A: placeholder router, no endpoints, not mounted
│       └── requests.py         # Phase 5E-A: placeholder router, no endpoints, not mounted
├── alembic/
│   ├── env.py                 # wired to app.config + app.database.Base.metadata
│   ├── script.py.mako
│   └── versions/
│       └── 45f5b1be1f76_initial_domain_models.py   # creates all 9 tables (Phase 5C; unchanged)
├── alembic.ini
├── tests/                       # Phase 5E-A: pytest suite (see "Testing" below)
│   ├── conftest.py              # isolated test DB/session, TestClient, account/scope factories
│   ├── test_auth_security.py    # password hashing + JWT contract (valid/malformed/bad-sig/expired/missing-claims)
│   ├── test_auth_login.py       # POST /auth/login (valid, wrong password, unknown login_id, inactive)
│   ├── test_auth_me.py          # GET /auth/me (valid, missing/invalid token, inactive, no password_hash leak)
│   ├── test_authorization.py    # require_role (permitted / wrong role)
│   └── test_scope.py            # association/federation/worker scope helpers
├── pytest.ini
├── requirements.txt
├── requirements-dev.txt         # Phase 5E-A: pytest, httpx2 (test-only, separate from requirements.txt)
├── .env.example
└── README.md
```

### Authentication (Phase 5D)

- `POST /auth/login` — body `{"login_id": "...", "password": "..."}`. On
  success, returns `{"access_token": "...", "token_type": "bearer",
  "account": {...}}`. On any failure (unknown `login_id`, wrong password,
  or an inactive account), returns `401` with the same generic
  `"Invalid login credentials"` message — deliberately not distinguishable,
  so the endpoint can't be used to enumerate which login_ids exist or
  learn *why* a login failed.
- `GET /auth/me` — requires `Authorization: Bearer <token>`; returns the
  caller's own account information. Never returns `password_hash` (the
  `AccountPublic` response model has no such field at all).
- Passwords are hashed with Argon2id (`argon2-cffi`), never stored or
  logged in plaintext, never returned by any response, and never placed
  in the JWT.
- Access tokens are JWTs (HS256, `PyJWT`) containing only `sub` (Account
  UUID), `role`, `iat`, `exp` — no organization IDs, no password/hash.
  There is no refresh token in Phase 5D; a token is simply valid until it
  expires (`ACCESS_TOKEN_EXPIRE_MINUTES`, default 30) or the account is
  deactivated (checked against the live database on every authenticated
  request — deactivating an account takes effect immediately, without any
  token-revocation mechanism).
- `app/auth/dependencies.py` exposes `get_current_account` (the one place
  that turns a Bearer token into a verified `Account`, re-checking
  existence and `is_active` against the database every time) and
  `require_role(*roles)` (server-side role enforcement — a client's own
  claimed role is never trusted). Both are meant to be reused by future
  protected routes, not reimplemented per-endpoint.
- `app/auth/scope.py` provides organization-scope **foundations** for
  future routes (not wired into any endpoint yet, since Phase 5D defines
  no business routes): deriving a WORKER's association from
  `Account -> Worker -> Association`, and confirming an
  `ASSOCIATION_ADMIN`/`FEDERATION_ADMIN` account's own association/
  federation membership — always from the authenticated account's own
  database relationships, never from a client-supplied id.

### Environment variables (Phase 5D additions)

```
JWT_SECRET_KEY=<a long random value — required, no default>
ACCESS_TOKEN_EXPIRE_MINUTES=30   # optional, defaults to 30 if omitted
```

Generate a real secret with, e.g., `python3 -c "import secrets; print(secrets.token_urlsafe(48))"`.

### API/error/pagination conventions (Phase 5E-A)

Foundation only — nothing below is wired into a business endpoint yet:

- `app/api/errors.py` — shared helpers for the status codes that don't
  already have an established home: `bad_request()` (400), `not_found()`
  (404), `conflict()` (409). 401/403 remain exactly where Phase 5D put
  them (`app/auth/dependencies.py`, `app/auth/scope.py`); 422 is automatic
  via Pydantic request validation. This is deliberately not a custom
  exception framework — every route still raises a plain FastAPI
  `HTTPException`, same as before.
- `app/schemas/pagination.py` — `PaginationParams` (1-indexed `page`,
  `page_size` bounded to 1–100, default 20) and a generic
  `PaginatedResponse` envelope, for future list endpoints to share
  instead of each inventing its own bounds.
- `app/api/users.py` / `workers.py` / `associations.py` / `federation.py`
  / `requests.py` — placeholder `APIRouter`s with no endpoints, not
  included in `app/main.py`. They exist only so a later phase has an
  obvious file to add real routes to; they currently have zero effect on
  the running application.

### Testing (Phase 5E-A)

A permanent, automated pytest suite lives in `backend/tests/`. It
converts the earlier Phase 5D manual verification into repeatable,
automated tests and **must never run against the real development
database** (`karmanya`).

**1. Create an isolated test database** (once), separate from the `karmanya`
development database:

```bash
sudo -u postgres psql -c "CREATE DATABASE karmanya_test OWNER karmanya;"
# or, without sudo/a postgres superuser role available:
createdb -O karmanya karmanya_test
```

**2. Install test dependencies** (in addition to `requirements.txt`):

```bash
pip install -r requirements-dev.txt
```

**3. Set `TEST_DATABASE_URL` and run pytest** from inside `backend/`:

```bash
export TEST_DATABASE_URL=postgresql://karmanya:karmanya@localhost:5432/karmanya_test
pytest
```

`TEST_DATABASE_URL` is required — `tests/conftest.py` fails immediately,
before any test runs, if it's unset, or if it happens to resolve to the
same value as the development `DATABASE_URL` (from an exported env var or
`backend/.env`). This is a hard safety check, not just documentation: the
suite forces `DATABASE_URL` to `TEST_DATABASE_URL` before importing any
`app.*` module, so even `app/database.py`'s module-level SQLAlchemy engine
is bound to the test database, never the development one.

The test database's schema is created directly from the SQLAlchemy models
(`Base.metadata.create_all`) at the start of the test run and dropped at
the end — deliberately **not** via Alembic, keeping the test suite fully
decoupled from the production migration tooling. Each individual test
runs inside a transaction that is rolled back afterward, so tests never
leak data into one another and no seed/demo data is ever left behind.

What's covered: password hashing, the JWT contract (valid / malformed /
invalid-signature / expired / missing-claims — tested directly against
`app/auth/security.py`), `/auth/login` (valid / wrong password / unknown
login_id / inactive account — all indistinguishable, per the Phase 5D
generic-401 design), `/auth/me` (valid / missing / malformed token /
deactivated-after-issuance / never exposes `password_hash`),
`require_role` (permitted / wrong role), and the association/federation/
worker scope helpers in `app/auth/scope.py`.

`backend/.env` (the developer's own local configuration) is never read or
modified by the test suite beyond the one-time comparison used for the
identical-URL safety check above.

### Running / testing auth locally

```bash
alembic upgrade head          # Phase 5C schema (unchanged by Phase 5D)
uvicorn app.main:app --reload
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"login_id": "some_login_id", "password": "some_password"}'
curl http://localhost:8000/auth/me -H "Authorization: Bearer <access_token>"
```

There is no signup endpoint in Phase 5D, so a test account needs its
`password_hash` set directly (e.g. via a short script calling
`app.auth.security.hash_password(...)` and inserting/updating the
`Account` row) — this is intentional per the locked scope: "do not add
permanent demo/seed accounts."

### Domain schema (Phase 5C)

Nine tables, locked hierarchy `Federation -> Association -> Worker`:
`federations`, `associations`, `accounts`, `user_profiles`, `workers`,
`services`, `worker_skills`, `service_requests`, `assignments`.

- Every primary key is a `UUID`. Human-readable identifiers
  (`workers.worker_code`, `service_requests.request_code`) are separate
  columns, not the primary key.
- Every status/role column (`accounts.role`, `workers.status`,
  `service_requests.status`, `assignments.status`) is a Python
  `enum.Enum`, persisted as `VARCHAR` **plus a database-level `CHECK`
  constraint** — never a native PostgreSQL `ENUM` type. See
  `app/models/type_decorators.py` for why `create_constraint=True` is
  required to actually get the `CHECK` (SQLAlchemy 2.0 does not add one
  by default).
- `service_requests.request_code` is generated by a dedicated PostgreSQL
  sequence (`request_code_seq`, created/dropped explicitly in the
  migration — autogenerate does not emit DDL for a `Sequence` declared
  purely as a column default) via a server-side default expression
  (`'REQ-' || lpad(nextval(...), 6, '0')`), so generation is atomic and
  race-free.
- `assignments` has **no unique constraint on `(request_id, worker_id)`**
  on purpose: a `ServiceRequest` accumulates a full history of
  `Assignment` attempts (declined, cancelled, eventually accepted) and a
  worker can legitimately be re-offered the same request later.
- Every one-to-many relationship whose child foreign key has an explicit
  `ondelete` (`CASCADE` or `RESTRICT`) is declared with
  `passive_deletes=True` on the parent side, so PostgreSQL — not
  SQLAlchemy nulling the child's FK first — is what actually enforces
  cascade/restrict behavior.
- No leave, availability, workload, or matching-score fields on `Worker`
  — deferred to a later phase. No `worker_id` on `ServiceRequest` — a
  request's current worker (if any) is derived from its `Assignment`
  history, never stored directly on the request.

### Running migrations

From inside `backend/` with the virtual environment active and
`DATABASE_URL` set (see below):

```bash
alembic upgrade head    # apply all migrations
alembic downgrade base  # roll back to an empty schema
alembic current          # show which revision is applied
```

`alembic/env.py` reads the database URL from `app.config.get_settings()`
— the same `DATABASE_URL` environment variable `app/main.py` uses — so
there is exactly one place the connection string is configured;
`alembic.ini`'s own `sqlalchemy.url` is intentionally left blank.

## 1. Create the Python environment

From inside `backend/`:

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
```

## 2. Install dependencies

```bash
pip install -r requirements.txt
```

## 3. Configure environment variables

```bash
cp .env.example .env
```

Then edit `.env` and set a real `DATABASE_URL` for your local PostgreSQL
instance. If you don't have PostgreSQL running locally yet, the quickest
options are:

- **Docker:** `docker run --name karmanya-db -e POSTGRES_USER=karmanya -e POSTGRES_PASSWORD=karmanya -e POSTGRES_DB=karmanya -p 5432:5432 -d postgres:16`
- **Local install:** create a database and user matching whatever
  `DATABASE_URL` you put in `.env` (e.g. `createuser karmanya` and
  `createdb -O karmanya karmanya`).

Note: `GET /health` itself still doesn't touch the database (SQLAlchemy's
engine only opens a real connection once something actually uses a
session), so the app can start without PostgreSQL reachable. A running
PostgreSQL instance **is** needed for the next step, since Phase 5C added
the domain schema and its Alembic migration.

## 4. Apply database migrations

```bash
alembic upgrade head
```

This creates the nine domain tables described above. See "Running
migrations" above for `downgrade`/`current`.

## 5. Start the development server

```bash
uvicorn app.main:app --reload
```

## 6. Check the health endpoint

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{"status": "ok", "environment": "development"}
```

Interactive API docs (auto-generated by FastAPI) are available at
`http://localhost:8000/docs` once the server is running.
