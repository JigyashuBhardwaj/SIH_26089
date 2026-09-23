"""
Phase 5D — authentication + authorization.

This package owns password hashing/verification, JWT issuance/decoding,
and the reusable FastAPI dependencies (`get_current_account`,
`require_role`) that future protected routes build on. It contains no
domain/business logic and defines no new database tables — the only
database model it reads from is the existing Phase 5C `Account`.
"""
