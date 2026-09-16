import type { Role } from '@shared/auth';

/**
 * Demo/local admin accounts for this prototype. There is no backend yet
 * — see `features/auth/AuthContext.tsx` for how this is consumed. Same
 * "mock now, real later" reasoning as the mobile app's `authService.ts`:
 * only this file's internals need to change once a real backend exists.
 *
 * These are FICTIONAL demo accounts — no real-world affiliation implied.
 */

export interface AssociationAccount {
  role: Extract<Role, 'ASSOCIATION_ADMIN'>;
  loginId: string;
  password: string;
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
  password: string;
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
 * Looks up a demo account by login ID + password. Throws with the exact
 * user-facing message the login screen should show — never reveals
 * whether the ID or the password was the specific problem.
 */
export function findAccount(loginId: string, password: string): DemoAccount {
  const account = DEMO_ACCOUNTS.find((entry) => entry.loginId === loginId && entry.password === password);
  if (!account) {
    throw new Error('Invalid ID or password.');
  }
  return account;
}
