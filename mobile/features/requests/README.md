# features/requests/

Local/demo request state for the User booking flow (Phase 3D).

- `RequestsContext.tsx` — the `RequestsProvider`/`useRequests()` React
  Context holding every request created via Confirm Request's "Send
  Request", plus `submitRequest`, `cancelRequest`, and `getRequest`. Same
  reasoning as `features/auth`: plain Context, no external state library.
- `index.ts` — barrel export; screens import from `features/requests`,
  never reach into `RequestsContext.tsx` directly.

There is no backend yet, so requests live only in memory for the current
app session. The `LocalServiceRequest` shape mirrors the shared `Booking`
concept (serviceId, associationId, status using the canonical
`BookingStatus`, address, createdAt) so replacing this with real API
calls later shouldn't require changing any screen that calls
`useRequests()`.
