import type { Role } from '@shared/auth';

/**
 * Demo/local admin account DISPLAY DATA for this prototype.
 *
 * Phase 6A: authentication itself is now real — `features/auth/AuthContext.tsx`
 * calls the actual backend `POST /auth/login`/`GET /auth/me` via
 * `services/authService.ts`, not `findFederationAccount`/
 * `findAssociationAccount` below. This file is kept as the source of
 * *display* fields (association name, worker count, rating, coverage,
 * federation display name, ...) that the dashboard/worker-list UI reads
 * but that have no equivalent on the real backend at all: the backend
 * `Association` model only has `id`/`federation_id`/`name` (no rating,
 * worker count, or coverage — see `backend/app/schemas/association.py`),
 * and the real `Account`/login response has no display name field.
 * `getAssociationDisplayByLoginId`/`getFederationDisplayByLoginId` below
 * are the mapping layer that resolves a real, authenticated account's
 * `loginId` to this display data, since it happens to describe exactly
 * the same demo dataset the backend's Phase 5F seed script creates.
 * `findFederationAccount`/`findAssociationAccount` (the old
 * password-checking lookups) are left in place, unused by AuthContext
 * now, in case something else in this file's history still references
 * them — see the exported functions' own docs for which is which.
 *
 * These are FICTIONAL demo accounts — no real-world affiliation implied.
 */

export interface AssociationAccount {
  role: Extract<Role, 'ASSOCIATION_ADMIN'>;
  loginId: string;
  /**
   * Optional: present on the static demo fixtures below, absent when
   * this shape is built from a real, already-authenticated backend
   * account (Phase 6A) — the real password is never held anywhere on
   * the client past the login request itself.
   */
  password?: string;
  /**
   * DISPLAY/PROTOTYPE id only, in this static catalogue's own format
   * (e.g. `'dhanbad_skilled'`) — never the real backend `Association`
   * UUID. When this shape is built from a real, authenticated backend
   * account (Phase 6A, see `features/auth/AuthContext.tsx`'s
   * `toDisplayAccount`), the authoritative backend id is
   * `account.associationId` on that real account, a separate value this
   * field must not be confused with or read as if it were.
   */
  associationId: string;
  associationName: string;
  services: string[];
  /** Same demo figure used on the mobile app's Select Association screen, for consistency. */
  workerCount: string;
  location: string;
  rating: number;
  coverage: string;
}

export interface FederationAccount {
  role: Extract<Role, 'FEDERATION_ADMIN'>;
  loginId: string;
  /** Optional — see `AssociationAccount.password`. */
  password?: string;
  name: string;
}

export type DemoAccount = AssociationAccount | FederationAccount;

export const DEMO_ACCOUNTS: DemoAccount[] = [
  {
    role: 'ASSOCIATION_ADMIN',
    loginId: 'dhanbad_skilled',
    password: 'skilled123',
    associationId: 'dhanbad_skilled',
    associationName: 'Dhanbad Skilled Workers Association',
    services: ['Plumbing', 'Electrical', 'Carpentry', 'Masonry'],
    workerCount: '120+',
    location: 'Dhanbad, Jharkhand',
    rating: 4.7,
    coverage: 'Dhanbad city & nearby areas',
  },
  {
    role: 'ASSOCIATION_ADMIN',
    loginId: 'dhanbad_general',
    password: 'general123',
    associationId: 'dhanbad_general',
    associationName: 'Dhanbad General Workers Association',
    services: ['Plumbing', 'Painting', 'Cleaning', 'Gardening', 'General Helpers'],
    workerCount: '95+',
    location: 'Dhanbad, Jharkhand',
    rating: 4.5,
    coverage: 'Dhanbad city & nearby areas',
  },
  {
    role: 'FEDERATION_ADMIN',
    loginId: 'federation_admin',
    password: 'federation123',
    name: 'Karmanya Federation Administration',
  },
];

/**
 * The two demo associations, for the Federation dashboard's
 * "Associations Overview" section. Derived from DEMO_ACCOUNTS rather than
 * duplicated, so there is exactly one place this data is defined.
 */
export function getAllAssociations(): AssociationAccount[] {
  return DEMO_ACCOUNTS.filter((account): account is AssociationAccount => account.role === 'ASSOCIATION_ADMIN');
}

/**
 * Same as the old generic lookup, but scoped to Federation accounts
 * only — used by the dedicated Federation Login page so a correct
 * Association ID/password typed there is still rejected as invalid, not
 * silently logged in as the wrong portal.
 */
export function findFederationAccount(loginId: string, password: string): FederationAccount {
  const account = DEMO_ACCOUNTS.find(
    (entry): entry is FederationAccount =>
      entry.role === 'FEDERATION_ADMIN' && entry.loginId === loginId && entry.password === password
  );
  if (!account) {
    throw new Error('Invalid ID or password.');
  }
  return account;
}

/** Same as `findFederationAccount`, but scoped to Association accounts only. */
export function findAssociationAccount(loginId: string, password: string): AssociationAccount {
  const account = DEMO_ACCOUNTS.find(
    (entry): entry is AssociationAccount =>
      entry.role === 'ASSOCIATION_ADMIN' && entry.loginId === loginId && entry.password === password
  );
  if (!account) {
    throw new Error('Invalid ID or password.');
  }
  return account;
}

/**
 * Phase 6A mapping layer: display data for a real, already-authenticated
 * Association account, looked up by `loginId` alone (no password check —
 * the real backend already verified the password). Returns `null` for a
 * login_id the static demo dataset doesn't describe (e.g. a genuine
 * future non-demo association account), so the caller can fall back to
 * safe placeholder values instead of crashing.
 */
export function getAssociationDisplayByLoginId(loginId: string): AssociationAccount | null {
  return DEMO_ACCOUNTS.find(
    (entry): entry is AssociationAccount => entry.role === 'ASSOCIATION_ADMIN' && entry.loginId === loginId
  ) ?? null;
}

/** Same as `getAssociationDisplayByLoginId`, but for Federation accounts. */
export function getFederationDisplayByLoginId(loginId: string): FederationAccount | null {
  return DEMO_ACCOUNTS.find(
    (entry): entry is FederationAccount => entry.role === 'FEDERATION_ADMIN' && entry.loginId === loginId
  ) ?? null;
}
