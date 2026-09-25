import type { Assignment } from '@shared/types';
import { getAccessToken } from './authService';
import { ApiError, NetworkUnavailableError, request } from './apiClient';

/**
 * Phase 6D: the Worker mobile app's own Assignment data — read via
 * `GET /workers/me/assignments`, responded to via
 * `POST /assignments/{assignment_id}/accept` and `.../decline`. Mirrors
 * the exact same fetch/pagination/error-handling shape already
 * established in `serviceCatalog.ts`/`associationCatalog.ts` and the
 * USER side's `RequestsContext.tsx` — no new HTTP abstraction, no new
 * state-management library.
 *
 * `Assignment` (`@shared/types`) already matches the backend's
 * `AssignmentPublic` field-for-field (camelCase, same field names, no
 * Decimal-typed fields), so — unlike `serviceCatalog.ts` — no raw/mapped
 * type split is needed here; the wire shape IS the shape the UI uses.
 */

/**
 * `GET /workers/me/assignments`'s largest accepted page size
 * (backend-enforced: `PaginationParams.page_size` caps at 100) — same
 * constant convention as every other paginated fetch in this app.
 */
const MAX_PAGE_SIZE = 100;

interface AssignmentListResponse {
  items: Assignment[];
  page: number;
  pageSize: number;
  total: number;
}

/**
 * Fetches the complete Assignment history for the authenticated worker
 * (no "active only" filter server-side — see `backend/app/api/workers.py`).
 * Screens that only care about currently-pending offers filter this
 * result themselves (`status === 'PENDING_RESPONSE'`), the same way
 * `ongoing-requests.tsx` filters `RequestsContext`'s full list rather
 * than the backend doing it.
 */
export async function fetchOwnAssignments(): Promise<Assignment[]> {
  const token = await getAccessToken();
  const collected: Assignment[] = [];
  let page = 1;

  for (;;) {
    const response = await request<AssignmentListResponse>(
      `/workers/me/assignments?page=${page}&page_size=${MAX_PAGE_SIZE}`,
      { token }
    );
    collected.push(...response.items);

    if (response.items.length === 0 || collected.length >= response.total) {
      break;
    }
    page += 1;
  }

  return collected;
}

/**
 * Accepts the authenticated worker's own PENDING_RESPONSE assignment.
 * Returns the backend's authoritative, post-accept `Assignment` — the
 * caller must use this response to update local state, never infer the
 * new status itself.
 */
export async function acceptAssignment(assignmentId: string): Promise<Assignment> {
  const token = await getAccessToken();
  return request<Assignment>(`/assignments/${assignmentId}/accept`, { method: 'POST', token });
}

/**
 * Declines the authenticated worker's own PENDING_RESPONSE assignment.
 * Returns the backend's authoritative, post-decline `Assignment` — same
 * never-fabricate rule as `acceptAssignment` above.
 */
export async function declineAssignment(assignmentId: string): Promise<Assignment> {
  const token = await getAccessToken();
  return request<Assignment>(`/assignments/${assignmentId}/decline`, { method: 'POST', token });
}

/**
 * Phase 6E-A: cancels the authenticated worker's own already-ACCEPTED
 * assignment (they can no longer perform the work). Returns the
 * backend's authoritative, post-cancel `Assignment` (status
 * `CANCELLED_BY_WORKER`) — same never-fabricate rule as
 * `acceptAssignment`/`declineAssignment` above.
 */
export async function cancelAssignment(assignmentId: string): Promise<Assignment> {
  const token = await getAccessToken();
  return request<Assignment>(`/assignments/${assignmentId}/cancel`, { method: 'POST', token });
}

/**
 * Phase 6E-A: marks the authenticated worker's own ACCEPTED assignment
 * as the completed job ("Mark Work as Done"). Returns the backend's
 * authoritative, post-complete `Assignment` (status `COMPLETED`) — the
 * linked ServiceRequest moves to `WORKER_COMPLETED` on the backend as
 * part of the same call, though that isn't reflected in this
 * `Assignment` response itself (the User side handles what happens next
 * separately, later, in `app/api/requests.py`).
 */
export async function completeAssignment(assignmentId: string): Promise<Assignment> {
  const token = await getAccessToken();
  return request<Assignment>(`/assignments/${assignmentId}/complete`, { method: 'POST', token });
}

/** Maps a `fetchOwnAssignments` failure to a safe, user-facing message. */
export function describeFetchAssignmentsError(err: unknown): string {
  if (err instanceof ApiError || err instanceof NetworkUnavailableError) {
    return err.message;
  }
  return 'Something went wrong while loading your booking requests. Please try again.';
}

/** Maps an `acceptAssignment` failure (other than a 409, which the caller reconciles by re-fetching) to a safe message. */
export function describeAcceptError(err: unknown): string {
  if (err instanceof ApiError || err instanceof NetworkUnavailableError) {
    return err.message;
  }
  return 'Could not accept this request. Please try again.';
}

/** Maps a `declineAssignment` failure (other than a 409) to a safe message. */
export function describeDeclineError(err: unknown): string {
  if (err instanceof ApiError || err instanceof NetworkUnavailableError) {
    return err.message;
  }
  return 'Could not decline this request. Please try again.';
}

/** Maps a `cancelAssignment` failure (other than a 409, reconciled by re-fetching) to a safe message. */
export function describeCancelError(err: unknown): string {
  if (err instanceof ApiError || err instanceof NetworkUnavailableError) {
    return err.message;
  }
  return 'Could not cancel this job. Please try again.';
}

/** Maps a `completeAssignment` failure (other than a 409, reconciled by re-fetching) to a safe message. */
export function describeCompleteError(err: unknown): string {
  if (err instanceof ApiError || err instanceof NetworkUnavailableError) {
    return err.message;
  }
  return 'Could not mark this job as done. Please try again.';
}
