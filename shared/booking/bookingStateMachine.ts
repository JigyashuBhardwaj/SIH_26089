import type { ServiceRequestStatus } from '../types/booking';

/**
 * Valid next states for each ServiceRequest status. This is data only —
 * it establishes the state machine's shape so the mobile app, Admin
 * Dashboard, and backend agree on it early. The functions that use this
 * table (canTransition, applyTransition) are implemented in Phase 7 once the
 * full booking flow exists end-to-end.
 *
 * Decline and post-acceptance worker cancellation are NOT request-level
 * transitions — they happen at the Assignment level (see
 * shared/types/booking.ts's AssignmentStatus) and both simply return the
 * request to MATCHING so it can be assigned again:
 *   - Assignment -> DECLINED           => ServiceRequest -> MATCHING
 *   - Assignment -> CANCELLED_BY_WORKER => ServiceRequest -> MATCHING
 * That's why ASSIGNED and ACCEPTED both list MATCHING as a valid next
 * state below, alongside their forward-progress transition.
 */
export const SERVICE_REQUEST_STATUS_TRANSITIONS: Record<ServiceRequestStatus, ServiceRequestStatus[]> = {
  PENDING: ['MATCHING', 'CANCELLED_BY_USER'],
  MATCHING: ['ASSIGNED', 'CANCELLED_BY_USER'],
  ASSIGNED: ['ACCEPTED', 'MATCHING', 'CANCELLED_BY_USER'],
  ACCEPTED: ['WORKER_COMPLETED', 'MATCHING', 'CANCELLED_BY_USER'],
  WORKER_COMPLETED: ['USER_CONFIRMED'],
  USER_CONFIRMED: ['PAYMENT_PENDING'],
  PAYMENT_PENDING: ['PAID'],
  PAID: ['COMPLETED'],
  COMPLETED: [],
  CANCELLED_BY_USER: [],
};
