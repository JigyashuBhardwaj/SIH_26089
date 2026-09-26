import React, { createContext, useCallback, useContext, useMemo, useState } from 'react';
import type { ServiceRequest, ServiceRequestStatus } from '@shared/types';
import { ApiError, NetworkUnavailableError, request as apiRequest } from '../../services/apiClient';
import { getAccessToken } from '../../services/authService';
import { fetchServiceCatalog } from '../../services/serviceCatalog';
import { fetchAssociationCatalog } from '../../services/associationCatalog';

/**
 * The exact dummy address/pincode used for every request in this demo
 * integration — there is no real user profile/address system yet (Phase
 * 6B-4 scope explicitly keeps it this way rather than adding one). These
 * are the two separate fields the backend's `POST /requests` contract
 * requires (`address`, `pincode`) — never the old combined
 * "<address> — <pincode>" display string, which the backend never saw.
 */
const DEMO_REQUEST_ADDRESS = 'House no. 108, Sector 4, Dhanbad, Jharkhand';
const DEMO_REQUEST_PINCODE = '826004';

/**
 * Retained for screens that still display the old combined string
 * (`confirm-request.tsx`'s "Service Location" summary row). Display-only
 * — never sent to the backend as-is; `submitRequest` below sends
 * `DEMO_REQUEST_ADDRESS`/`DEMO_REQUEST_PINCODE` as separate fields.
 */
export const DEMO_ADDRESS = `${DEMO_REQUEST_ADDRESS} — ${DEMO_REQUEST_PINCODE}`;

/**
 * `GET /requests`'s largest accepted page size (backend-enforced, same
 * `PaginationParams.page_size <= 100` cap as `GET /services` /
 * `GET /associations`).
 */
const MAX_PAGE_SIZE = 100;

/** `GET /requests`'s paginated envelope — mirrors `ServiceRequestListResponse`. */
interface RequestsListResponse {
  items: ServiceRequest[];
  page: number;
  pageSize: number;
  total: number;
}

/**
 * Formats an ISO `requestedDateTime` the same way `schedule.tsx` formats
 * the `Date` the user picked — kept as a small local duplicate (rather
 * than importing from `schedule.tsx`, which exports no such helper)
 * since this is the only file that needs to re-derive a display label
 * from a backend-returned ISO string rather than a freshly-picked Date.
 */
function formatRequestedDateTimeLabel(isoDateTime: string): string {
  const date = new Date(isoDateTime);
  const dateLabel = date.toLocaleDateString(undefined, {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  });
  const timeLabel = date.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit', hour12: true });
  return `${dateLabel}, ${timeLabel}`;
}

/** Maps a `loadRequests` failure to a safe, user-facing message — same pattern as the catalogue fetchers. */
function describeLoadRequestsError(err: unknown): string {
  if (err instanceof NetworkUnavailableError) {
    return err.message;
  }
  if (err instanceof ApiError) {
    return err.message;
  }
  return 'Something went wrong while loading your requests. Please try again.';
}

export type RequestsLoadState = 'idle' | 'loading' | 'error' | 'ready';

/**
 * A submitted service request, as tracked on the USER mobile app.
 *
 * Phase 6B-4: `submitRequest` now calls the real `POST /requests` and
 * this shape carries the authoritative, server-owned fields from that
 * response (`requestId` <- `ServiceRequestPublic.id`, `requestCode`,
 * `status`, `requestedDateTime`, `address`, `pincode`, `createdAt`,
 * `updatedAt`) verbatim — none of them are ever fabricated client-side
 * anymore. `serviceName`/`associationName`/`dateTimeLabel` remain
 * UI-only convenience fields the backend does not return (a real join
 * the backend doesn't perform for this response); they're carried
 * through from what was already known at submit time, purely for
 * display, and never override or substitute for a backend-owned field.
 */
export interface LocalServiceRequest {
  // Backend-authoritative fields (from ServiceRequestPublic) — always
  // taken from the POST /requests response, never fabricated.
  requestId: string;
  requestCode: string;
  serviceId: string;
  associationId: string;
  requestedDateTime: string;
  address: string;
  pincode: string;
  status: ServiceRequestStatus;
  createdAt: string;
  updatedAt: string;
  // Phase 6E-B: backend-authoritative assigned-worker fields (from
  // `ServiceRequestPublic`, Phase 6E-A) — `undefined`/`null` until the
  // backend's current Assignment for this request reaches ACCEPTED or
  // COMPLETED. Populated only by `loadRequests`'s `GET /requests`
  // mapping below; `submitRequest`'s `POST /requests` response never has
  // them set (a brand-new request has no Assignment yet), and neither
  // `confirmRequest` nor `payRequest` patch them locally — see those
  // functions' own comments for why.
  assignedWorkerId?: string | null;
  assignedWorkerName?: string | null;
  assignedWorkerPhone?: string | null;
  // UI-only convenience fields — not part of the backend response.
  serviceName: string;
  associationName: string;
  dateTimeLabel: string;
}

/**
 * What `submitRequest` needs. `serviceId`/`associationId`/
 * `requestedDateTime` are the real backend fields sent to `POST
 * /requests`; `serviceName`/`associationName`/`dateTimeLabel` are
 * UI-only and never sent to the backend.
 */
export interface SubmitRequestInput {
  serviceId: string;
  serviceName: string;
  requestedDateTime: string;
  dateTimeLabel: string;
  associationId: string;
  associationName: string;
}

interface RequestsContextValue {
  requests: LocalServiceRequest[];
  loadState: RequestsLoadState;
  loadError: string | null;
  loadRequests: () => Promise<void>;
  submitRequest: (input: SubmitRequestInput) => Promise<LocalServiceRequest>;
  cancelRequest: (requestId: string) => Promise<void>;
  confirmRequest: (requestId: string) => Promise<void>;
  payRequest: (requestId: string) => Promise<void>;
  getRequest: (requestId: string) => LocalServiceRequest | undefined;
}

const RequestsContext = createContext<RequestsContextValue | undefined>(undefined);

/**
 * Request store for the USER app.
 *
 * Phase 6B-4: `submitRequest` calls the real, authenticated
 * `POST /requests` (via the existing `apiClient.request<T>()` +
 * `authService.getAccessToken()` — no second HTTP/error abstraction).
 * The returned `ServiceRequestPublic` is authoritative for every
 * server-owned field; this store only adds the UI-only display fields
 * the backend doesn't return.
 *
 * Phase 6B-5: `loadRequests` makes `GET /requests` the authoritative
 * source for the full list — it replaces `requests` wholesale with the
 * freshly fetched, freshly re-resolved list (deduplicating by the real
 * backend `id` is therefore automatic: the fetched list simply *becomes*
 * `requests`, so a request `submitRequest` already inserted locally is
 * naturally superseded rather than duplicated once a load succeeds).
 * `submitRequest`'s immediate local insert is unchanged and still lets
 * `request-submitted.tsx` display the new request without waiting on a
 * `GET /requests` round-trip.
 *
 * Phase 6B-6: `cancelRequest` now calls the real, authenticated
 * `POST /requests/{id}/cancel` (same `apiClient.request<T>()` +
 * `authService.getAccessToken()` pattern as `submitRequest`/
 * `loadRequests` — no second HTTP/error abstraction). It never updates
 * local state before the backend confirms the cancellation, and on
 * success it only patches the one affected row's `status`/`updatedAt` —
 * a full `GET /requests` reload isn't needed for that case. Reconciling
 * with the backend on a 409 (the request turned out not to be
 * cancellable anymore) is the caller's responsibility via the existing
 * `loadRequests()`, not something this function does itself.
 */
export function RequestsProvider({ children }: { children: React.ReactNode }) {
  const [requests, setRequests] = useState<LocalServiceRequest[]>([]);
  const [loadState, setLoadState] = useState<RequestsLoadState>('idle');
  const [loadError, setLoadError] = useState<string | null>(null);

  const loadRequests = useCallback(async (): Promise<void> => {
    setLoadState('loading');
    setLoadError(null);

    try {
      // 1. Fetch every page of GET /requests, driven by the
      // server-reported `total` — never assumed to fit on one page.
      // Same loop pattern as fetchServiceCatalog/fetchAssociationCatalog.
      const token = await getAccessToken();
      const collected: ServiceRequest[] = [];
      let page = 1;
      for (;;) {
        const response = await apiRequest<RequestsListResponse>(
          `/requests?page=${page}&page_size=${MAX_PAGE_SIZE}`,
          { token }
        );
        collected.push(...response.items);
        if (response.items.length === 0 || collected.length >= response.total) {
          break;
        }
        page += 1;
      }

      // 2. Resolve the UI-only display fields the backend doesn't
      // return, from the existing live catalogues. A catalogue fetch
      // failure doesn't fail the whole load — it just falls back to a
      // safe placeholder per item, since the request list itself
      // (authoritative) is more important than its display names.
      const [services, associations] = await Promise.all([
        fetchServiceCatalog().catch(() => []),
        fetchAssociationCatalog().catch(() => []),
      ]);
      const serviceNameById = new Map(services.map((service) => [service.id, service.name]));
      const associationNameById = new Map(associations.map((association) => [association.id, association.name]));

      const normalized: LocalServiceRequest[] = collected.map((item) => ({
        requestId: item.id,
        requestCode: item.requestCode,
        serviceId: item.serviceId,
        associationId: item.associationId,
        requestedDateTime: item.requestedDateTime,
        address: item.address,
        pincode: item.pincode,
        status: item.status,
        createdAt: item.createdAt,
        updatedAt: item.updatedAt,
        assignedWorkerId: item.assignedWorkerId,
        assignedWorkerName: item.assignedWorkerName,
        assignedWorkerPhone: item.assignedWorkerPhone,
        serviceName: serviceNameById.get(item.serviceId) ?? 'Unknown service',
        associationName: associationNameById.get(item.associationId) ?? 'Unknown association',
        dateTimeLabel: formatRequestedDateTimeLabel(item.requestedDateTime),
      }));

      // 3. GET /requests is authoritative for the complete list —
      // replace wholesale rather than merging, so nothing local/stale
      // survives a successful load.
      setRequests(normalized);
      setLoadState('ready');
    } catch (err) {
      setLoadError(describeLoadRequestsError(err));
      setLoadState('error');
    }
  }, []);

  const submitRequest = useCallback(async (input: SubmitRequestInput): Promise<LocalServiceRequest> => {
    const token = await getAccessToken();
    const response = await apiRequest<ServiceRequest>('/requests', {
      method: 'POST',
      token,
      body: {
        serviceId: input.serviceId,
        associationId: input.associationId,
        requestedDateTime: input.requestedDateTime,
        address: DEMO_REQUEST_ADDRESS,
        pincode: DEMO_REQUEST_PINCODE,
      },
    });

    const newRequest: LocalServiceRequest = {
      requestId: response.id,
      requestCode: response.requestCode,
      serviceId: response.serviceId,
      associationId: response.associationId,
      requestedDateTime: response.requestedDateTime,
      address: response.address,
      pincode: response.pincode,
      status: response.status,
      createdAt: response.createdAt,
      updatedAt: response.updatedAt,
      serviceName: input.serviceName,
      associationName: input.associationName,
      dateTimeLabel: input.dateTimeLabel,
    };
    setRequests((previous) => [newRequest, ...previous]);
    return newRequest;
  }, []);

  const cancelRequest = useCallback(async (requestId: string): Promise<void> => {
    const token = await getAccessToken();
    const response = await apiRequest<ServiceRequest>(`/requests/${requestId}/cancel`, {
      method: 'POST',
      token,
    });

    // Backend is authoritative for this row. Cancellation never changes
    // serviceId/associationId/requestedDateTime, so the existing UI-only
    // serviceName/associationName/dateTimeLabel are simply left as-is —
    // only the two backend-owned fields the cancel actually changed
    // (status, updatedAt) are patched in. No optimistic update happens
    // before this point: this function is only ever called after the
    // request has already resolved successfully.
    setRequests((previous) =>
      previous.map((request) =>
        request.requestId === response.id
          ? { ...request, status: response.status, updatedAt: response.updatedAt }
          : request
      )
    );
  }, []);

  /**
   * Phase 6E-B: the authenticated user confirms that the worker's
   * completed job is done (`POST /requests/{id}/confirm`). Unlike
   * `cancelRequest` above, this deliberately does NOT patch `status`
   * locally from the mutation's own response — that response is
   * unenriched by design (Phase 6E-B decision: mutation-response
   * enrichment is out of scope; `GET /requests` remains the one
   * authoritative, enriched source) and the backend is authoritative for
   * the resulting status either way, so a full `loadRequests()` re-fetch
   * is what actually reflects it, with no locally-guessed state in
   * between. A thrown `ApiError`/`NetworkUnavailableError` (e.g. a 409 —
   * the request was no longer WORKER_COMPLETED) propagates to the
   * caller, which reconciles via its own `loadRequests()` call exactly
   * like the existing cancel flow does.
   */
  const confirmRequest = useCallback(
    async (requestId: string): Promise<void> => {
      const token = await getAccessToken();
      await apiRequest<ServiceRequest>(`/requests/${requestId}/confirm`, {
        method: 'POST',
        token,
      });
      await loadRequests();
    },
    [loadRequests]
  );

  /**
   * Phase 6E-B: the authenticated user completes the demo payment step
   * (`POST /requests/{id}/pay`) — no real payment gateway, no card
   * details collected here or anywhere else in this app. Same
   * never-locally-patch, always-re-fetch rationale as `confirmRequest`
   * above.
   */
  const payRequest = useCallback(
    async (requestId: string): Promise<void> => {
      const token = await getAccessToken();
      await apiRequest<ServiceRequest>(`/requests/${requestId}/pay`, {
        method: 'POST',
        token,
      });
      await loadRequests();
    },
    [loadRequests]
  );

  const getRequest = useCallback(
    (requestId: string) => requests.find((request) => request.requestId === requestId),
    [requests]
  );

  const value = useMemo<RequestsContextValue>(
    () => ({
      requests,
      loadState,
      loadError,
      loadRequests,
      submitRequest,
      cancelRequest,
      confirmRequest,
      payRequest,
      getRequest,
    }),
    [
      requests,
      loadState,
      loadError,
      loadRequests,
      submitRequest,
      cancelRequest,
      confirmRequest,
      payRequest,
      getRequest,
    ]
  );

  return <RequestsContext.Provider value={value}>{children}</RequestsContext.Provider>;
}

/** Access the local request store. Must be used under RequestsProvider. */
export function useRequests(): RequestsContextValue {
  const context = useContext(RequestsContext);
  if (!context) {
    throw new Error('useRequests must be used within a RequestsProvider.');
  }
  return context;
}
