import { createSeededRandom, intBetween, pick } from './seededRandom';

/**
 * Synthetic worker dataset for Phase 4B (Worker Database & Availability).
 *
 * IMPORTANT — how this is "static": the 215 records below are built by a
 * small deterministic generator (seeded PRNG, not `Math.random()`) rather
 * than typed out by hand one at a time. The seed never changes, so the
 * generator always produces the exact same 215 records, in the same
 * order, with the same fields, on every run/reload/build — there is no
 * runtime randomness a demo could ever see differ. This keeps the data
 * internally coherent (workload matches assignment count, "On Leave"
 * matches an actual leave period, etc.) without hand-authoring 215
 * separate literal objects.
 *
 * These are entirely FICTIONAL demo workers — no real people, phone
 * numbers, or addresses.
 */

export type AvailabilityStatus = 'Available' | 'Busy' | 'Unavailable' | 'On Leave';
export type WorkerStatus = 'Active' | 'Inactive';
export type AssignmentStatus = 'Scheduled' | 'In Progress';
export type LeaveStatus = 'Approved';

export interface LeavePeriod {
  startDate: string; // ISO date (YYYY-MM-DD)
  endDate: string; // ISO date (YYYY-MM-DD)
  status: LeaveStatus;
}

export interface Assignment {
  requestId: string;
  service: string;
  scheduledDate: string; // ISO date (YYYY-MM-DD)
  scheduledTime: string; // e.g. "10:00 AM"
  status: AssignmentStatus;
}

export interface Worker {
  workerId: string;
  fullName: string;
  phoneNumber: string;
  address: string;
  pincode: string;
  associationId: string;
  associationName: string;
  skills: string[];
  rating: number;
  totalJobsCompleted: number;
  /**
   * The worker's baseline workload/assignment count — NOT necessarily
   * what should be displayed. Use `getEffectiveWorkload(worker)` /
   * `getEffectiveAssignments(worker)` instead, which return 0/[] while
   * the worker is effectively On Leave or Unavailable, without losing
   * this stored baseline (so it reappears correctly once leave ends).
   */
  currentWorkload: number;
  /**
   * The worker's BASE availability — only ever 'Available' | 'Busy' |
   * 'Unavailable'. This is NOT what should be displayed directly: use
   * `getEffectiveAvailability(worker)` instead, which layers the
   * inactive-worker rule and the currently-active-leave check on top of
   * this using the real current date. Kept as a stored field (rather than
   * only "workload") so an explicitly-unavailable worker (e.g. taking a
   * break from new jobs) is distinguishable from one who simply has no
   * workload right now.
   */
  availabilityStatus: AvailabilityStatus;
  workerStatus: WorkerStatus;
  upcomingLeave: LeavePeriod | null;
  /** Baseline assignment list — see the note on `currentWorkload` above; use `getEffectiveAssignments(worker)` for display. */
  currentAssignments: Assignment[];
}

// ---------------------------------------------------------------------------
// Fixed name-part pools (fictional). Combined deterministically per worker.
// ---------------------------------------------------------------------------

const FIRST_NAMES = [
  'Rajesh', 'Suresh', 'Amit', 'Vijay', 'Sanjay', 'Manoj', 'Ramesh', 'Ashok',
  'Dinesh', 'Anil', 'Prakash', 'Sunil', 'Rakesh', 'Naresh', 'Mahesh', 'Deepak',
  'Vikram', 'Ravi', 'Sandeep', 'Pankaj', 'Arjun', 'Rohit', 'Vivek', 'Alok',
  'Santosh', 'Mukesh', 'Yogesh', 'Bimal', 'Kamal', 'Gopal', 'Birsa', 'Somra',
  'Sunita', 'Rekha', 'Kavita', 'Pooja', 'Anita', 'Meena', 'Geeta', 'Sarita',
  'Nirmala', 'Kiran', 'Shanti', 'Usha', 'Lata', 'Radha', 'Sushma', 'Manju',
] as const;

const LAST_NAMES = [
  'Kumar', 'Singh', 'Sharma', 'Verma', 'Yadav', 'Das', 'Mahato', 'Roy',
  'Prasad', 'Thakur', 'Mandal', 'Hembrom', 'Soren', 'Oraon', 'Mishra',
  'Choudhary', 'Ram', 'Gope', 'Rana', 'Sahu', 'Turi', 'Baski',
] as const;

const COLONY_NAMES = [
  'Ambedkar Colony', 'Ashok Nagar', 'Vivekanand Colony', 'Shastri Nagar',
  'Gandhi Colony', 'Nehru Nagar', 'Subhash Colony', 'Model Colony',
  'Station Road Colony', 'New Basti', 'Ward 5 Colony', 'Ward 9 Colony',
] as const;

// Real-format-looking but clearly-Dhanbad-demo PIN codes (existing demo geography).
const PINCODES = ['826001', '826002', '826003', '826004', '826005'] as const;

interface AssociationSeed {
  associationId: string;
  associationName: string;
  skillPool: readonly string[];
  count: number;
  idPrefix: string;
  seed: number;
}

// Uses the existing Phase 4A demo association IDs/names — no new
// association is created here.
const ASSOCIATION_SEEDS: AssociationSeed[] = [
  {
    associationId: 'dhanbad_skilled',
    associationName: 'Dhanbad Skilled Workers Association',
    skillPool: ['Plumber', 'Electrician', 'Carpenter', 'Mason', 'Painter', 'Water Heater Technician', 'Helper'],
    count: 120,
    idPrefix: 'SKW',
    seed: 20260914,
  },
  {
    associationId: 'dhanbad_general',
    associationName: 'Dhanbad General Workers Association',
    skillPool: ['Plumber', 'Painter', 'Cleaner', 'Gardener', 'Helper'],
    count: 95,
    idPrefix: 'GEN',
    seed: 20260915,
  },
];

/**
 * The anchor used ONLY to generate plausible, deterministic calendar
 * dates for leave windows and assignment schedules (e.g. "this worker's
 * leave runs 2026-09-13 to 2026-09-16"). Computed from the real current
 * date at module-load time — not a hardcoded literal — so the generated
 * windows stay meaningfully "around now" no matter when this app is run,
 * rather than permanently clustering around one fixed historical date
 * and eventually drifting entirely into the past. The seeded offsets
 * applied on top of this anchor are what keep the dataset deterministic;
 * only the anchor point itself tracks real time. This is NOT used to
 * decide whether a worker is *currently* on leave — that comparison
 * always uses the real current date directly (see `isLeaveActive` /
 * `getEffectiveAvailability` below).
 */
const LEAVE_GENERATION_ANCHOR = (() => {
  const now = new Date();
  return new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()));
})();

function isoDateOffset(days: number): string {
  const date = new Date(LEAVE_GENERATION_ANCHOR);
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}

function generateWorkersForAssociation(seed: AssociationSeed): Worker[] {
  const random = createSeededRandom(seed.seed);
  const workers: Worker[] = [];
  let requestCounter = 1;

  for (let i = 0; i < seed.count; i++) {
    const workerNumber = i + 1;
    const workerId = `${seed.idPrefix}-${String(workerNumber).padStart(4, '0')}`;

    const fullName = `${pick(random, FIRST_NAMES)} ${pick(random, LAST_NAMES)}`;

    // Round-robin the primary skill so every service the association
    // supports is guaranteed multiple capable workers, then optionally
    // add 1-2 more distinct skills for realism.
    const primarySkill = seed.skillPool[i % seed.skillPool.length];
    const skills = new Set<string>([primarySkill]);
    const extraSkillCount = intBetween(random, 0, 2);
    for (let s = 0; s < extraSkillCount; s++) {
      skills.add(pick(random, seed.skillPool));
    }

    const houseNumber = intBetween(random, 1, 400);
    const colony = pick(random, COLONY_NAMES);
    const pincode = pick(random, PINCODES);
    const address = `House No. ${houseNumber}, ${colony}, Dhanbad, Jharkhand`;

    // Clearly synthetic, sequential phone numbers — not real numbers.
    // Includes an association-specific block offset so numbers stay
    // globally unique across both associations, not just within one.
    const associationBlock = seed.idPrefix === 'SKW' ? 0 : 20000;
    const phoneNumber = `+91-90000-${String(associationBlock + 10000 + workerNumber).slice(-5)}`;

    const rating = Math.round((4.0 + random() * 1.0) * 10) / 10; // 4.0 - 5.0
    const totalJobsCompleted = intBetween(random, 5, 260);

    // Base availability distribution: roughly 60% Available, 25% Busy,
    // 15% Unavailable. "On Leave" is never stored here — it's always
    // derived at read-time from whether upcomingLeave is currently
    // active (see getEffectiveAvailability), so it stays correct as real
    // time passes rather than being frozen at generation time.
    const availabilityRoll = random();
    let availabilityStatus: AvailabilityStatus;
    if (availabilityRoll < 0.6) availabilityStatus = 'Available';
    else if (availabilityRoll < 0.85) availabilityStatus = 'Busy';
    else availabilityStatus = 'Unavailable';

    // Leave windows are fixed calendar-date offsets from the anchor above,
    // generated independently of the base availability roll. Roughly 12%
    // of workers get a window that covers "now" at generation time (so a
    // realistic slice of the workforce is on leave whenever the app is
    // opened), and a further ~8% get a genuinely future window. Whether
    // either is *currently* active is always re-checked dynamically
    // against the real current date at read time (see `isLeaveActive`),
    // never frozen here.
    let upcomingLeave: LeavePeriod | null = null;
    const leaveRoll = random();
    if (leaveRoll < 0.12) {
      const startOffset = intBetween(random, -3, 0);
      const duration = intBetween(random, 2, 6);
      upcomingLeave = {
        startDate: isoDateOffset(startOffset),
        endDate: isoDateOffset(startOffset + duration),
        status: 'Approved',
      };
    } else if (leaveRoll < 0.2) {
      const startOffset = intBetween(random, 7, 30);
      const duration = intBetween(random, 2, 5);
      upcomingLeave = {
        startDate: isoDateOffset(startOffset),
        endDate: isoDateOffset(startOffset + duration),
        status: 'Approved',
      };
    }

    // Workload/assignments are stored purely from the baseline
    // availability roll, deliberately independent of the leave window
    // above. Whether a currently-active leave should suppress workload
    // for *display* is handled dynamically at read time (see
    // `getEffectiveWorkload`/`getEffectiveAssignments`) — storing it
    // pre-zeroed here would freeze that decision to whatever "now" was
    // at generation time and never revisit it once the leave ends.
    let currentWorkload: number;
    if (availabilityStatus === 'Busy') currentWorkload = intBetween(random, 2, 6);
    else if (availabilityStatus === 'Available') currentWorkload = intBetween(random, 0, 1);
    else currentWorkload = 0; // Unavailable: not taking active jobs right now.

    const currentAssignments: Assignment[] = [];
    for (let a = 0; a < currentWorkload; a++) {
      const service = pick(random, Array.from(skills));
      currentAssignments.push({
        requestId: `REQ-${seed.idPrefix}-${String(requestCounter).padStart(5, '0')}`,
        service,
        scheduledDate: isoDateOffset(intBetween(random, 0, 6)),
        scheduledTime: pick(random, ['9:00 AM', '10:00 AM', '11:00 AM', '1:00 PM', '2:00 PM', '4:00 PM', '6:00 PM']),
        status: pick(random, ['Scheduled', 'In Progress'] as const),
      });
      requestCounter++;
    }

    // A small fraction of workers are Inactive (e.g. dormant accounts).
    const workerStatus: WorkerStatus = random() < 0.05 ? 'Inactive' : 'Active';

    workers.push({
      workerId,
      fullName,
      phoneNumber,
      address,
      pincode,
      associationId: seed.associationId,
      associationName: seed.associationName,
      skills: Array.from(skills),
      rating,
      totalJobsCompleted,
      currentWorkload,
      availabilityStatus,
      workerStatus,
      upcomingLeave,
      currentAssignments,
    });
  }

  return workers;
}

/** The full synthetic dataset: 120 Skilled + 95 General = 215 workers. */
export const WORKERS: Worker[] = ASSOCIATION_SEEDS.flatMap(generateWorkersForAssociation);

export function getWorkersByAssociation(associationId: string): Worker[] {
  return WORKERS.filter((worker) => worker.associationId === associationId);
}

export function getWorkerById(workerId: string): Worker | undefined {
  return WORKERS.find((worker) => worker.workerId === workerId);
}

/** Today's date as YYYY-MM-DD, in UTC — matches how leave/assignment dates are stored, so comparisons are plain string comparisons with no timezone-shift risk. */
export function getTodayISODate(referenceDate: Date = new Date()): string {
  return referenceDate.toISOString().slice(0, 10);
}

/**
 * Whether an approved leave period is active on the given date (inclusive
 * of both the start and end date). Plain ISO-string comparison — since
 * both sides are YYYY-MM-DD with no time component, this can't suffer
 * the off-by-one errors that comparing full Date objects across
 * timezones can.
 */
export function isLeaveActive(leave: LeavePeriod | null, referenceDate: Date = new Date()): boolean {
  if (!leave) return false;
  const today = getTodayISODate(referenceDate);
  return leave.startDate <= today && today <= leave.endDate;
}

/**
 * The availability that should actually be displayed/filtered on —
 * always computed against the real current date, never a fixed stored
 * value. Priority order:
 *   1. Inactive workers are always effectively Unavailable, regardless
 *      of anything else (including an active leave).
 *   2. A currently-active approved leave means On Leave.
 *   3. Otherwise, the worker's baseline availability applies as-is.
 */
export function getEffectiveAvailability(worker: Worker, referenceDate: Date = new Date()): AvailabilityStatus {
  if (worker.workerStatus === 'Inactive') return 'Unavailable';
  if (isLeaveActive(worker.upcomingLeave, referenceDate)) return 'On Leave';
  return worker.availabilityStatus;
}

/**
 * The workload that should actually be displayed — 0 whenever the
 * worker is effectively Unavailable or On Leave (inactive workers and
 * workers currently on leave aren't taking active jobs right now), even
 * though the stored `currentWorkload` reflects their baseline. This is
 * what keeps availability and workload visually consistent after a
 * worker's leave ends: their stored baseline workload/assignments are
 * still there, so they don't need to be regenerated.
 */
export function getEffectiveWorkload(worker: Worker, referenceDate: Date = new Date()): number {
  const effective = getEffectiveAvailability(worker, referenceDate);
  return effective === 'On Leave' || effective === 'Unavailable' ? 0 : worker.currentWorkload;
}

/** Mirrors `getEffectiveWorkload`, but for the assignment list itself. */
export function getEffectiveAssignments(worker: Worker, referenceDate: Date = new Date()): Assignment[] {
  return getEffectiveWorkload(worker, referenceDate) > 0 ? worker.currentAssignments : [];
}

export interface WorkerFilterOptions {
  skill?: string;
  availabilityStatus?: AvailabilityStatus;
  workerStatus?: WorkerStatus;
  workloadBucket?: 'none' | 'light' | 'high' | 'heavy';
  associationId?: string;
}

function matchesWorkloadBucket(workload: number, bucket: WorkerFilterOptions['workloadBucket']): boolean {
  if (!bucket) return true;
  if (bucket === 'none') return workload === 0;
  if (bucket === 'light') return workload >= 1 && workload <= 2;
  if (bucket === 'high') return workload >= 3 && workload <= 4;
  return workload >= 5; // heavy
}

/** Search (name / worker ID / phone) + filters, combined — matches the "Search + Skill + Availability" example in the spec. */
export function searchAndFilterWorkers(
  workers: Worker[],
  query: string,
  filters: WorkerFilterOptions = {}
): Worker[] {
  const normalizedQuery = query.trim().toLowerCase();

  return workers.filter((worker) => {
    if (normalizedQuery) {
      const matchesQuery =
        worker.fullName.toLowerCase().includes(normalizedQuery) ||
        worker.workerId.toLowerCase().includes(normalizedQuery) ||
        worker.phoneNumber.toLowerCase().includes(normalizedQuery);
      if (!matchesQuery) return false;
    }

    if (filters.associationId && worker.associationId !== filters.associationId) return false;
    if (filters.skill && !worker.skills.includes(filters.skill)) return false;
    if (filters.availabilityStatus && getEffectiveAvailability(worker) !== filters.availabilityStatus) return false;
    if (filters.workerStatus && worker.workerStatus !== filters.workerStatus) return false;
    if (!matchesWorkloadBucket(getEffectiveWorkload(worker), filters.workloadBucket)) return false;

    return true;
  });
}
