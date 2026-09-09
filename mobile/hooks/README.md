# hooks/

Shared custom React hooks used across the User and Worker flows.

- **useComingSoon.ts** — pairs with `components/ComingSoonDialog.tsx`;
  wraps the open/close state so screens don't repeat `useState`
  boilerplate for the same dialog.

More are added alongside the features that first need them (e.g. a
future `useBooking(id)` once `services/` has real booking calls).
