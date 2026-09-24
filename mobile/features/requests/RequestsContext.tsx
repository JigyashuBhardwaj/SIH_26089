import React, { createContext, useCallback, useContext, useMemo, useState } from 'react';
import type { ServiceRequest, ServiceRequestStatus } from '@shared/types';
import { request as apiRequest } from '../../services/apiClient';
import { getAccessToken } from '../../services/authService';

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
  submitRequest: (input: SubmitRequestInput) => Promise<LocalServiceRequest>;
  cancelRequest: (requestId: string) => void;
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
 * the backend doesn't return. Submitted requests still live only in
 * this session's memory (no `GET /requests` yet, per locked scope) —
 * `cancelRequest` also remains local-only for the same reason.
 */
export function RequestsProvider({ children }: { children: React.ReactNode }) {
  const [requests, setRequests] = useState<LocalServiceRequest[]>([]);

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

  const cancelRequest = useCallback((requestId: string) => {
    setRequests((previous) =>
      previous.map((request) =>
        request.requestId === requestId ? { ...request, status: 'CANCELLED_BY_USER' } : request
      )
    );
  }, []);

  const getRequest = useCallback(
    (requestId: string) => requests.find((request) => request.requestId === requestId),
    [requests]
  );

  const value = useMemo<RequestsContextValue>(
    () => ({ requests, submitRequest, cancelRequest, getRequest }),
    [requests, submitRequest, cancelRequest, getRequest]
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
