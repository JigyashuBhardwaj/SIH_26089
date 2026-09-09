# backend/

The single central backend/API that `mobile/` and `admin/` both talk to.
Owns the database and is the authoritative enforcer of booking rules and
state transitions defined in `../shared/booking` (client-side copies of
those rules are for UI responsiveness only, never the security/consistency
boundary).

Not started yet. Provider/framework choice is made explicitly at the
start of Phase 4 — nothing here should be assumed ahead of that
conversation.
