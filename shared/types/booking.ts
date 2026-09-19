/**
 * The full ServiceRequest lifecycle. Order reflects the happy path;
 * CANCELLED_BY_USER branches off it. See
 * shared/booking/bookingStateMachine.ts for valid transitions.
 *
 * There are deliberately no request-level IN_PROGRESS, DECLINED,
 * REASSIGNING, or CANCELLED_BY_WORKER states. Decline and
 * post-acceptance worker cancellation are represented purely as
 * Assignment-level outcomes (see AssignmentStatus below) — the request
 * itself just returns to MATCHING in both cases.
 */
export type ServiceRequestStatus =
  | 'PENDING'
  | 'MATCHING'
  | 'ASSIGNED'
  | 'ACCEPTED'
  | 'WORKER_COMPLETED'
  | 'USER_CONFIRMED'
  | 'PAYMENT_PENDING'
  | 'PAID'
  | 'COMPLETED'
  | 'CANCELLED_BY_USER';

/**
 * A user's service request. This is the central object shared by the
 * User app, Worker app, Association Admin portal, and Federation view —
 * every client displays the current state of the same request.
 *
 * The current worker relationship is intentionally NOT modeled here as a
 * single `workerId` field: a request can go through multiple Assignment
 * attempts over its lifetime (decline, worker cancellation, etc.), and
 * that history must be preserved rather than overwritten. To find the
 * current or historical worker(s) for a request, look up Assignment
 * records where `Assignment.requestId` matches this request's `id`.
 */
export interface ServiceRequest {
  id: string;
  requestCode: string;
  userId: string;
  associationId: string;
  serviceId: string;
  status: ServiceRequestStatus;
  address: string;
  pincode: string;
  /** ISO timestamp of the requested service time. */
  requestedServiceTime: string;
  /** ISO timestamp of when the request was created. */
  createdAt: string;
  /** ISO timestamp of the most recent status/field change. */
  updatedAt: string;
}

/**
 * One attempt to give a ServiceRequest to a specific worker. A request
 * can have many Assignment records over time — previous attempts are
 * never overwritten, only superseded, so the full assignment history
 * (who was offered the job, who declined, who cancelled, who completed
 * it) stays auditable.
 */
export type AssignmentStatus = 'PENDING_RESPONSE' | 'ACCEPTED' | 'DECLINED' | 'CANCELLED_BY_WORKER' | 'COMPLETED';

export interface Assignment {
  id: string;
  requestId: string;
  workerId: string;
  /** The association-admin account id that made this assignment. */
  assignedBy: string;
  status: AssignmentStatus;
  /** ISO timestamp of when this assignment was made. */
  assignedAt: string;
  /** ISO timestamp of when the worker responded (accepted/declined), or null if still pending. */
  respondedAt: string | null;
}
