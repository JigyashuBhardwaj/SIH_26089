import React, { createContext, useCallback, useContext, useMemo, useState } from 'react';
import type { BookingStatus } from '@shared/types';

/**
 * The exact dummy address used for every request in this prototype —
 * there is no real user profile/address system yet (see Phase 3D scope).
 */
export const DEMO_ADDRESS = 'House no. 108, Sector 4, Dhanbad, Jharkhand — 826004';

/**
 * A locally-created service request. The field set mirrors the shared
 * `Booking` concept (serviceId, associationId, status, address,
 * createdAt) plus a few display-only convenience fields (serviceName,
 * dateTimeLabel, associationName) that a real backend response would
 * normally resolve via a join — since there's no backend here, this
 * prototype just carries them directly. `status` reuses the canonical
 * `BookingStatus` from `shared/types` rather than inventing a new enum.
 */
export interface LocalServiceRequest {
  requestId: string;
  serviceId: string;
  serviceName: string;
  dateTimeLabel: string;
  associationId: string;
  associationName: string;
  address: string;
  status: BookingStatus;
  createdAt: string;
}

export interface SubmitRequestInput {
  serviceId: string;
  serviceName: string;
  dateTimeLabel: string;
  associationId: string;
  associationName: string;
}

function generateRequestId(): string {
  const stamp = Date.now().toString(36).toUpperCase();
  const random = Math.floor(Math.random() * 1000)
    .toString()
    .padStart(3, '0');
  return `REQ-${stamp}-${random}`;
}

interface RequestsContextValue {
  requests: LocalServiceRequest[];
  submitRequest: (input: SubmitRequestInput) => LocalServiceRequest;
  cancelRequest: (requestId: string) => void;
  getRequest: (requestId: string) => LocalServiceRequest | undefined;
}

const RequestsContext = createContext<RequestsContextValue | undefined>(undefined);

/**
 * Local/demo request store. No backend exists yet, so submitted requests
 * live only in memory for the current app session — same "mock now, real
 * later" reasoning as `authService.ts` and `serviceCatalog.ts`. When a
 * real backend arrives, only this file's internals need to change
 * (fetches instead of local state); the screens that call `useRequests()`
 * shouldn't need to.
 */
export function RequestsProvider({ children }: { children: React.ReactNode }) {
  const [requests, setRequests] = useState<LocalServiceRequest[]>([]);

  const submitRequest = useCallback((input: SubmitRequestInput): LocalServiceRequest => {
    const newRequest: LocalServiceRequest = {
      ...input,
      requestId: generateRequestId(),
      address: DEMO_ADDRESS,
      // This prototype skips the transient PENDING flash-state a real
      // backend might briefly occupy — the request is considered
      // "Finding a Worker" (MATCHING) the moment it's sent. See
      // shared/booking/bookingStateMachine.ts for the full transition
      // table; the actual PENDING->MATCHING transition isn't implemented
      // here, per Phase 3D scope.
      status: 'MATCHING',
      createdAt: new Date().toISOString(),
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
