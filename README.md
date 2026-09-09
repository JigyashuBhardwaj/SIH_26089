# SIH 26089 — Gig Worker Platform

SIH 2026 Problem Statement 26089. One central backend and one shared
booking model serve three connected surfaces:

- **`mobile/`** — a single Expo React Native app containing both the User
  flow and the Worker flow, separated by role-aware navigation (not two
  separate apps).
- **`admin/`** — the labour federation/association web dashboard.
- **`backend/`** — the single central API/backend both of the above talk to.
- **`shared/`** — framework-agnostic TypeScript (domain types, roles,
  booking rules/state machine, matching contract) consumed by `mobile/`
  and `admin/` so booking logic is never duplicated.
- **`docs/`** — project documentation.

## Status

Foundation/architecture only. No feature UI, authentication, backend,
database, payment, matching algorithm, or AI forecasting has been built
yet — see each folder's README for what phase adds it.

## Running the mobile app

```bash
cd mobile
npm start        # or: npm run android / npm run ios / npm run web
```

or, from the repo root:

```bash
npm run mobile
```

## Repo layout

```
SIH_26089/
├── mobile/     # Expo Router app: (auth), (user), (worker) route groups
├── admin/      # Admin Dashboard (not started)
├── backend/    # Backend/API (not started)
├── shared/     # Shared types, roles, booking rules, matching contract
└── docs/
```
