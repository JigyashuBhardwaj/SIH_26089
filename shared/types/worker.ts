/**
 * A worker verified and onboarded by a labour association/federation.
 * Workers do not self-register — credentials are issued by an admin
 * (see Admin Dashboard, Phase 5).
 *
 * Phase 6A: field names/shape corrected to match the actual backend
 * `WorkerPublic` response (`backend/app/schemas/worker.py`) exactly —
 * this interface previously described fields (`name`, `phoneNumber` as
 * non-nullable, `skills`, `pinCode`, `isAvailable`) that do not exist on
 * the real `Worker` model. Nothing in `mobile/` or `admin/` consumed
 * this interface at the time of this correction, so this is a type-only
 * change with no behavior impact.
 */
export type WorkerStatus = 'ACTIVE' | 'INACTIVE';

export interface Worker {
  id: string;
  accountId: string;
  associationId: string;
  workerCode: string;
  fullName: string;
  /** Nullable on the backend — a worker's phone is not always recorded. */
  phoneNumber: string | null;
  status: WorkerStatus;
  address: string;
  pincode: string;
  /** 0–5 rating, as a plain number (backend returns a decimal). */
  rating: number;
  totalJobsCompleted: number;
  createdAt: string;
  updatedAt: string;
  // Deliberately no `skills` field: skills are modeled as a separate
  // WorkerSkill join table on the backend, not an array on Worker
  // itself, and no route currently returns them embedded here.
}
