# services/

All backend/API communication for the mobile app lives here — the only
place that calls `fetch`/a networking client (once a backend exists).
`features/` and route screens call functions exported from here; they
never talk to the network directly. This is what keeps backend
communication isolated from UI (architectural principle #7).

**`authService.ts`** (Phase 2) — mock/local authentication. Compares
credentials against an in-memory list and returns a `Promise<AuthSession>`
or throws an `Error`. Not secure, not persisted — a placeholder with the
exact shape real backend calls will have, so `features/auth` doesn't need
to change when Phase 4 replaces this file's internals with real HTTP
requests.
