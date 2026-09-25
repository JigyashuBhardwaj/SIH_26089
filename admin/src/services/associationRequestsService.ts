import type { ServiceRequest } from '@shared/types/booking';
import { ApiError, NetworkUnavailableError, request } from './apiClient';
import { getAccessToken } from './authService';

export { ApiError, NetworkUnavailableError };

/**
 * Phase 6C: integrates the Association Admin portal with the real
 * `/associations/me/*` request/assignment endpoints, plus the existing
 * `/services` catalogue (reused, read-only, to resolve a request's
 * `serviceId` into a human-readable name).
 *
 * Reuses the existing `apiClient.request()`/`ApiError`/
 * `NetworkUnavailableError` — no new HTTP abstraction — and the existing
 * Admin JWT via `getAccessToken()`. Every `/associations/me/*` call below
 * derives its association scope from that token server-side; none of
 * them ever send an `associationId`, `userId`, or `federationId`.
 *
 * Pagination follows the same `page_size=100` loop already established
 * in `mobile/services/serviceCatalog.ts` / `associationCatalog.ts` /
 * `RequestsContext.tsx`'s `loadRequests`: request pages of 100 until all
 * `total` items are collected.
 */

const PAGE_SIZE = 100;

interface PaginatedResponse<T> {
  items: T[];
  page: number;
  pageSize: number;
  total: number;
}

async function fetchAllPages<T>(pathForPage: (page: number) => string): Promise<T[]> {
  const token = getAccessToken();
  const collected: T[] = [];
  let page = 1;

  while (true) {
    const response = await request<PaginatedResponse<T>>(pathForPage(page), { token });
    collected.push(...response.items);
    if (collected.length >= response.total || response.items.length === 0) {
      break;
    }
    page += 1;
  }

  return collected;
}

/**
 * One eligible Worker for a specific ServiceRequest, as returned by
 * `GET /associations/me/requests/{requestId}/candidates`
 * (`backend/app/schemas/candidate.py::CandidatePublic`). Admin-local by
 * design — this does not belong in `shared/types`. Deliberately has no
 * "score" field: the backend exposes the three ranking factors directly
 * (`samePincode`, `activeAssignmentCount`, `rating`) instead of an opaque
 * number, and this interface mirrors that exactly.
 */
export interface Candidate {
  workerId: string;
  workerCode: string;
  fullName: string;
  phoneNumber: string | null;
  address: string;
  pincode: string;
  rating: number;
  totalJobsCompleted: number;
  activeAssignmentCount: number;
  samePincode: boolean;
}

/** One entry from the `/services` catalogue — only what's needed to resolve a name. */
export interface ServiceCatalogueEntry {
  id: string;
  name: string;
}

/**
 * All ServiceRequests belonging to the authenticated admin's own
 * association, in the backend's own order (newest first). Backend
 * authoritative — no client-side sort/filter.
 */
export async function fetchOwnAssociationRequests(): Promise<ServiceRequest[]> {
  return fetchAllPages<ServiceRequest>((page) => `/associations/me/requests?page=${page}&page_size=${PAGE_SIZE}`);
}

/** A single ServiceRequest belonging to the authenticated admin's own association. */
export async function fetchOwnAssociationRequest(requestId: string): Promise<ServiceRequest> {
  const token = getAccessToken();
  return request<ServiceRequest>(`/associations/me/requests/${requestId}`, { token });
}

/**
 * Eligible candidates for a ServiceRequest, in the backend's own
 * deterministic ranking order. Never re-ranked, re-sorted, or filtered
 * here — the backend order is authoritative.
 */
export async function fetchCandidates(requestId: string): Promise<Candidate[]> {
  return fetchAllPages<Candidate>(
    (page) => `/associations/me/requests/${requestId}/candidates?page=${page}&page_size=${PAGE_SIZE}`
  );
}

/**
 * Manually assigns `workerId` to `requestId`. On success (201) the
 * caller must re-fetch `fetchOwnAssociationRequest` and treat that as
 * authoritative — this function never infers/returns a locally-computed
 * status.
 */
export async function createAssignment(requestId: string, workerId: string): Promise<void> {
  const token = getAccessToken();
  await request(`/associations/me/requests/${requestId}/assignments`, {
    method: 'POST',
    body: { workerId },
    token,
  });
}

/**
 * The full `/services` catalogue, fetched once (paginated) and reused by
 * both the request list and detail pages to resolve `serviceId` ->
 * service name, rather than one request per ServiceRequest.
 */
export async function fetchServiceCatalogue(): Promise<ServiceCatalogueEntry[]> {
  const token = getAccessToken();
  const collected: ServiceCatalogueEntry[] = [];
  let page = 1;

  while (true) {
    const response = await request<PaginatedResponse<ServiceCatalogueEntry>>(
      `/services?page=${page}&page_size=${PAGE_SIZE}`,
      { token }
    );
    collected.push(...response.items);
    if (collected.length >= response.total || response.items.length === 0) {
      break;
    }
    page += 1;
  }

  return collected;
}

/** Builds a `serviceId -> serviceName` lookup from a fetched catalogue. */
export function buildServiceNameMap(services: ServiceCatalogueEntry[]): Map<string, string> {
  return new Map(services.map((service) => [service.id, service.name]));
}

/** Safe, user-facing message for a failed list/detail/catalogue fetch. */
export function describeFetchError(err: unknown): string {
  if (err instanceof ApiError || err instanceof NetworkUnavailableError) {
    return err.message;
  }
  return 'Something went wrong loading this data. Please try again.';
}

/** Safe, user-facing message for a failed candidate-discovery call, beyond the 409 case (handled by the caller via re-fetch). */
export function describeCandidatesError(err: unknown): string {
  if (err instanceof ApiError || err instanceof NetworkUnavailableError) {
    return err.message;
  }
  return 'Could not load candidates. Please try again.';
}

/** Safe, user-facing message for a failed assignment attempt. */
export function describeAssignError(err: unknown): string {
  if (err instanceof ApiError || err instanceof NetworkUnavailableError) {
    return err.message;
  }
  return 'Could not assign this worker. Please try again.';
}
