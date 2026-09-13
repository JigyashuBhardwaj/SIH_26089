# admin/ — Karmanya Association & Federation Web Portal

A React + TypeScript + Vite web application, separate from the `mobile/`
Expo project. It imports domain types from `../shared` the same way
`mobile/` does (via a `@shared/*` alias — see `vite.config.ts` and
`tsconfig.app.json`).

## Status: Phase 4A — Foundation + Demo Login

This phase is the web app's foundation: a login screen, local/demo
authentication, and role-based dashboard shells. There is no backend yet
— see `src/data/demoAccounts.ts` for the demo accounts and
`src/features/auth/` for the session logic (same "mock now, real later"
pattern as the mobile app's `authService.ts`).

**Implemented:** login, logout, role-based routing (`ASSOCIATION_ADMIN`
vs `FEDERATION_ADMIN`), dashboard shell (header + sidebar), Association
and Federation dashboard content with static demo metrics, and a Coming
Soon page for the not-yet-built nav items (Requests, Workers,
Associations, Analytics).

**Not implemented yet** (later phases): request management, worker
management, matching/assignment, backend/API, database, payment,
notifications, real association/federation data.

## Demo accounts

| Login ID | Password | Role |
|---|---|---|
| `dhanbad_skilled` | `skilled123` | Association Admin — Dhanbad Skilled Workers Association |
| `dhanbad_general` | `general123` | Association Admin — Dhanbad General Workers Association |
| `federation_admin` | `federation123` | Federation Admin — Karmanya Federation Administration |

These are fictional demo accounts for this prototype only.

## Running locally

```bash
cd admin
npm install
npm run dev      # starts the Vite dev server
npm run build    # type-checks (tsc -b) and produces a production build
npm run preview  # serves the production build locally
```

## Known prototype inconsistency

The association IDs used here (`dhanbad_skilled`, `dhanbad_general`) are
plain login-style IDs, whereas the mobile app's demo association catalog
(`mobile/services/associationCatalog.ts`) uses hyphenated IDs
(`dhanbad-skilled-workers`, `dhanbad-general-workers`) for the *same* two
fictional associations. There is no backend yet to reconcile these, so
they're intentionally left as separate demo datasets for now — this
should be unified once a real backend/association directory exists.
