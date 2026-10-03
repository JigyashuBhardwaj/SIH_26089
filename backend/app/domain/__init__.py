"""
Domain-level business-rule helpers shared across multiple API routers.

This package exists because Phase 7C's leave business rules (calendar-day
counting, annual quota calculation, overlap detection, assignment-conflict
detection) and the existing Phase 5E-C service-request booking-horizon rule
all depend on the identical "what calendar day is this timestamp, in
Asia/Kolkata" primitive, and several of the leave rules are each needed by
two different future routers (worker leave submission and
association-admin leave approval) once those endpoints exist.

This is NOT a general service-layer introduction. Every other business
rule in this codebase remains inline in its own route function, exactly as
before (see `app/api/*.py`) -- this package holds only the handful of pure,
read-only primitives whose reuse across multiple call sites would
otherwise risk two independent, silently-drifting implementations of the
same rule. No ownership/authorization checks, no row-locking, and no API
routes live here; those belong to whichever endpoint actually performs a
write, per the Phase 7C-C investigation report.
"""
