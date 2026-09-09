# features/auth/

Auth feature logic used by the `(auth)` route group.

**Implemented in Phase 2:**
- `AuthContext.tsx` — the `AuthProvider`/`useAuth()` React Context that
  holds the current mock session (`null` when logged out) and exposes
  `loginAsUser`, `signUpAsUser`, `loginAsWorker`, and `logout`. This is
  the only piece of global state in the app — plain Context, no external
  state-management library.
- `index.ts` — barrel export; screens import from `features/auth`, never
  reach into `AuthContext.tsx` or `services/authService.ts` directly.

The actual mock login/signup logic lives in
`mobile/services/authService.ts`, not here — this folder only adapts that
service to React state. See that file's comments for what changes when a
real backend is introduced in Phase 4.
