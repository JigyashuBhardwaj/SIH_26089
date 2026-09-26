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
 *
 * Phase 6A: corrected to match the actual backend `ServiceRequestPublic`
 * response (`backend/app/schemas/request.py`) exactly — that response
 * deliberately never includes `userId` (a caller only ever sees their
 * own requests, so it's redundant, and the schema's own docstring notes
 * it's omitted on purpose), and the requested-time field is named
 * `requestedDateTime` on the backend, not `requestedServiceTime`.
 * Nothing in `mobile/` or `admin/` consumed this interface at the time
 * of this correction, so this is a type-only change with no behavior
 * impact.
 */
export interface ServiceRequest {
  id: string;
  requestCode: string;
  associationId: string;
  serviceId: string;
  status: ServiceRequestStatus;
  address: string;
  pincode: string;
  /** ISO timestamp of the requested service time. */
  requestedDateTime: string;
  /** ISO timestamp of when the request was created. */
  createdAt: string;
  /** ISO timestamp of the most recent status/field change. */
  updatedAt: string;
  /**
   * Phase 6E-B: the request's currently assigned worker, once one exists.
   * Matches `backend/app/schemas/request.py`'s `ServiceRequestPublic`
   * (Phase 6E-A) exactly — all three are `undefined`/`null` until the
   * backend's current Assignment for this request reaches ACCEPTED or
   * COMPLETED (never at PENDING/MATCHING/ASSIGNED, and never for a
   * superseded DECLINED/CANCELLED_BY_WORKER attempt). Optional here
   * rather than required so this interface still describes the create
   * (`POST /requests`) response truthfully too, where these are always
   * absent.
   */
  assignedWorkerId?: string | null;
  assignedWorkerName?: string | null;
  assignedWorkerPhone?: string | null;
}

/**
 * One attempt to give a ServiceRequest to a specific worker. A request
 * can have many Assignment records over time — previous attempts are
 * never overwritten, only superseded, so the full assignment history
 * (who was offered the job, who declined, who cancelled, who completed
 * it) stays auditable.
 */
export type AssignmentStatus = 'PENDING_RESPONSE' | 'ACCEPTED' | 'DECLINED' | 'CANCELLED_BY_WORKER' | 'COMPLETED';

/**
 * Phase 6E-A: a minimal, read-only snapshot of the ServiceRequest a
 * Worker-facing Assignment belongs to — joined server-side from the
 * existing ServiceRequest/Service tables (`backend/app/api/workers.py`'s
 * `list_own_assignments`), never a second, independently-stored source
 * of truth. Matches `backend/app/schemas/assignment.py`'s
 * `AssignmentRequestSummary` field-for-field.
 */
export interface AssignmentRequestSummary {
  requestCode: string;
  serviceName: string;
  /** ISO timestamp of the requested service time. */
  requestedDateTime: string;
  address: string;
  pincode: string;
}

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
  /** ISO timestamp of the most recent status change (Phase 6A: added to match backend `AssignmentPublic`). */
  updatedAt: string;
  /**
   * Phase 6E-A: present only on `GET /workers/me/assignments` responses
   * (`backend/app/schemas/assignment.py`'s `WorkerAssignmentPublic`) —
   * every other Assignment-returning endpoint (accept/decline/cancel/
   * complete, and the association-admin assignment-creation route)
   * returns the plain, unenriched shape and this field is simply absent
   * there. Optional here so this one shared interface still describes
   * both shapes truthfully; a consumer that only ever sees the worker
   * list (like `mobile/services/workerAssignments.ts`) can still rely on
   * it being present in practice, but must handle `undefined` gracefully
   * for defense-in-depth (e.g. an older cached value).
   */
  requestSummary?: AssignmentRequestSummary;
}
