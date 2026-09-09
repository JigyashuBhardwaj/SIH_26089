import type { BookingStatus } from '../types/booking';

/**
 * Valid next states for each booking status. This is data only — it
 * establishes the state machine's shape so the mobile app, Admin Dashboard,
 * and backend agree on it early. The functions that use this table
 * (canTransition, applyTransition) are implemented in Phase 7 once the
 * full booking flow exists end-to-end.
 */
export const BOOKING_STATUS_TRANSITIONS: Record<BookingStatus, BookingStatus[]> = {
  PENDING: ['MATCHING', 'CANCELLED_BY_USER'],
  MATCHING: ['ASSIGNED', 'CANCELLED_BY_USER'],
  ASSIGNED: ['ACCEPTED', 'DECLINED', 'REASSIGNING', 'CANCELLED_BY_USER'],
  ACCEPTED: ['IN_PROGRESS', 'CANCELLED_BY_USER', 'CANCELLED_BY_WORKER'],
  IN_PROGRESS: ['WORKER_COMPLETED', 'CANCELLED_BY_WORKER'],
  WORKER_COMPLETED: ['USER_CONFIRMED'],
  USER_CONFIRMED: ['PAYMENT_PENDING'],
  PAYMENT_PENDING: ['PAID'],
  PAID: ['COMPLETED'],
  COMPLETED: [],
  DECLINED: ['REASSIGNING'],
  REASSIGNING: ['ASSIGNED', 'CANCELLED_BY_USER'],
  CANCELLED_BY_USER: [],
  CANCELLED_BY_WORKER: ['REASSIGNING'],
};
