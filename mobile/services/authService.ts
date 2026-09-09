import type { Role } from '@shared/auth';

/**
 * Mock/local authentication service for Phase 2.
 *
 * This is NOT secure and NOT production authentication — passwords are
 * compared in plain text against an in-memory list, and nothing is
 * persisted across app restarts. It exists only so the role-selection ->
 * login -> role-specific-home navigation flow can be demonstrated before
 * a real backend exists.
 *
 * Every function here is written to be a drop-in replacement target:
 * same inputs, same return shape (a Promise<AuthSession> or a thrown
 * Error), so Phase 4 can swap the implementation for real API calls
 * without changing AuthContext or any screen.
 */

export type MobileRole = Extract<Role, 'USER' | 'WORKER'>;

export interface AuthSession {
  role: MobileRole;
  username: string;
  displayName: string;
}

interface MockAccountRecord {
  username: string;
  password: string;
  displayName: string;
}

/**
 * Seeded demo User account. See mobile/features/auth/README.md for the
 * documented demo credentials.
 */
const mockUserAccounts: MockAccountRecord[] = [
  { username: 'demo_user', password: 'user123', displayName: 'Demo User' },
];

/**
 * Seeded demo Worker account. In the real system, worker accounts are
 * created/provisioned by the Federation — there is no worker signup, so
 * this list is never appended to by the app itself.
 */
const mockWorkerAccounts: MockAccountRecord[] = [
  { username: 'demo_worker', password: 'worker123', displayName: 'Demo Worker' },
];

function simulateNetworkDelay<T>(value: T): Promise<T> {
  // A short delay so loading states behave the way a real network call
  // will later, without needing any networking library yet.
  return new Promise((resolve) => setTimeout(() => resolve(value), 300));
}

export async function loginAsUser(username: string, password: string): Promise<AuthSession> {
  const match = mockUserAccounts.find(
    (account) => account.username === username && account.password === password
  );
  if (!match) {
    throw new Error('Incorrect username or password.');
  }
  return simulateNetworkDelay({ role: 'USER', username: match.username, displayName: match.displayName });
}

export async function signUpAsUser(params: {
  fullName: string;
  username: string;
  password: string;
}): Promise<AuthSession> {
  const { fullName, username, password } = params;
  if (mockUserAccounts.some((account) => account.username === username)) {
    throw new Error('That username is already taken.');
  }
  mockUserAccounts.push({ username, password, displayName: fullName });
  return simulateNetworkDelay({ role: 'USER', username, displayName: fullName });
}

export async function loginAsWorker(username: string, password: string): Promise<AuthSession> {
  const match = mockWorkerAccounts.find(
    (account) => account.username === username && account.password === password
  );
  if (!match) {
    throw new Error('Incorrect Worker ID or password.');
  }
  return simulateNetworkDelay({ role: 'WORKER', username: match.username, displayName: match.displayName });
}

// Deliberately no signUpAsWorker export: workers do not self-register.
