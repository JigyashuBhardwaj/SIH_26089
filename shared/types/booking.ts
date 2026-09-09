/**
 * The full booking lifecycle. Order reflects the happy path; the
 * cancellation, decline, and reassignment states branch off it.
 * See shared/booking/bookingStateMachine.ts for valid transitions.
 */
export type BookingStatus =
  | 'PENDING'
  | 'MATCHING'
  | 'ASSIGNED'
  | 'ACCEPTED'
  | 'IN_PROGRESS'
  | 'WORKER_COMPLETED'
  | 'USER_CONFIRMED'
  | 'PAYMENT_PENDING'
  | 'PAID'
  | 'COMPLETED'
  | 'CANCELLED_BY_USER'
  | 'CANCELLED_BY_WORKER'
  | 'DECLINED'
  | 'REASSIGNING';

export interface Booking {
  id: string;
  userId: string;
  workerId?: string;
  associationId: string;
  serviceId: string;
  status: BookingStatus;
  address: string;
  /** ISO timestamp of the requested service time. */
  requestedServiceTime: string;
  /** ISO timestamp of when the booking request was created. */
  createdAt: string;
}
