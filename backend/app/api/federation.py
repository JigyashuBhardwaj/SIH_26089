"""
Placeholder router for future federation-related domain routes.

No endpoints are defined yet -- Phase 5E-A establishes API file
organization only (see the project's Phase 5E-A specification: "Do not
create actual domain/business endpoints merely to populate these
files"). This router is intentionally NOT included in `app/main.py` yet;
a later phase adds real endpoints here and mounts it.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/federation", tags=["federation"])
