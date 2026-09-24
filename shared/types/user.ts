/**
 * A person who books services through the mobile app's User flow.
 *
 * Phase 6A: corrected to match the actual backend `UserProfilePublic`
 * response (`backend/app/schemas/user.py`) exactly — this interface
 * previously had a `name` field (backend calls it `fullName`) and an
 * `address?` field that has no counterpart on the backend `UserProfile`
 * model at all (see that schema's own docstring: address was explicitly
 * deferred, not just omitted from this response). Nothing in `mobile/`
 * or `admin/` consumed this interface at the time of this correction, so
 * this is a type-only change with no behavior impact.
 */
export interface User {
  id: string;
  accountId: string;
  fullName: string;
  /** Nullable on the backend — a user's phone is not always recorded. */
  phoneNumber: string | null;
}
