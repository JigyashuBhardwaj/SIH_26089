# hooks/

Shared custom React hooks used across the User and Worker flows.

- **useComingSoon.ts** — pairs with `components/ComingSoonDialog.tsx`;
  wraps the open/close state so screens don't repeat `useState`
  boilerplate for the same dialog.
- **usePollingRefresh.ts** — Phase 6G: focus-aware background polling for
  a single screen, calling that screen's own existing reload function on
  an interval. Never fetches anything itself.

More are added alongside the features that first need them (e.g. a
future `useBooking(id)` once `services/` has real booking calls).
