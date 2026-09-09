# shared/

Framework-agnostic TypeScript shared by `mobile/`, `admin/`, and eventually
`backend/`. Plain `.ts` files — no build step, no npm package, no framework
imports (no React/React Native here).

- **types/** — domain entities: `User`, `Worker`, `Association`, `Service`,
  `Payment`, `Booking` (with `BookingStatus`).
- **auth/** — the `Role` union (`USER`, `WORKER`, `ASSOCIATION_ADMIN`,
  `FEDERATION_ADMIN`). Permission logic is added once real auth exists
  (Phase 2).
- **booking/** — booking rule constants/signatures and the status
  transition table. Implementations land in Phase 3/4/7; only the
  contract is defined now.
- **matching/** — the worker-matching criteria contract. The actual
  scoring algorithm lands in Phase 5 with the Admin Dashboard, and stays a
  deterministic algorithm, not ML.

## How this is consumed

`mobile/` resolves this folder via a TypeScript path alias
(`@shared/*` → `../shared/*`, see `mobile/tsconfig.json`) and a Metro
`watchFolders` entry (see `mobile/metro.config.js`) so Metro can bundle
files that live outside the `mobile/` project root. `admin/` will do the
same once it exists. This avoids needing npm workspaces for what is, for
now, a handful of plain type files.
