import * as SecureStore from 'expo-secure-store';
import type { Role } from '@shared/auth';
import { ApiError, NetworkUnavailableError, request } from './apiClient';

/**
 * Real backend authentication (Phase 6A).
 *
 * `POST /auth/login` and `GET /auth/me` are the only two endpoints this
 * phase integrates. Everything else about a session — the mobile app's
 * USER/WORKER role split, the shape screens consume via `AuthContext` —
 * is preserved unchanged; only how a session is obtained changed.
 *
 * Note: unlike every other backend response (which uses camelCase field
 * names via Pydantic aliases), `AccountPublic`/`LoginResponse`
 * (`backend/app/schemas/auth.py`) have no aliases at all, so the raw
 * wire response for these two endpoints uses snake_case field names
 * (`login_id`, `is_active`, `access_token`, ...). This file maps that
 * raw shape to the app's normalized camelCase `AuthAccount` shape
 * (`shared/types/account.ts`) at the boundary, rather than letting the
 * inconsistency leak into the rest of the app.
 */

export type MobileRole = Extract<Role, 'USER' | 'WORKER'>;

export interface AuthSession {
  role: MobileRole;
  username: string;
  displayName: string;
}

const TOKEN_KEY = 'karmanya_access_token';

/** Raw `/auth/login` and `/auth/me` wire shape — see the module docstring above. */
interface RawAccount {
  id: string;
  login_id: string;
  role: Role;
  is_active: boolean;
  association_id: string | null;
  federation_id: string | null;
  created_at: string;
  updated_at: string;
}

interface RawLoginResponse {
  access_token: string;
  token_type: string;
  account: RawAccount;
}

function isMobileRole(role: Role): role is MobileRole {
  return role === 'USER' || role === 'WORKER';
}

/**
 * Thrown by `toSession` when a token belongs to a real, valid account
 * that just isn't a USER/WORKER account. Distinct from `ApiError` so
 * `restoreSession` can tell "this token will never work for this
 * client" apart from "the backend rejected/couldn't verify the token" —
 * see that function's docstring.
 */
class WrongAccountTypeError extends Error {}

function toSession(account: RawAccount): AuthSession {
  if (!isMobileRole(account.role)) {
    // An Admin-portal account authenticating through the mobile app's
    // endpoints shouldn't happen, but guard against it rather than
    // producing a session with an invalid `role`.
    throw new WrongAccountTypeError('This account is not a User or Worker account.');
  }
  return {
    role: account.role,
    username: account.login_id,
    // The account/login row has no display name of its own (that lives
    // on the separate UserProfile/Worker record, which this phase's
    // scope doesn't call) — the login ID is what's shown until a later
    // integration phase wires up GET /users/me or GET /workers/me.
    displayName: account.login_id,
  };
}

function sessionFromAccount(account: RawAccount, expectedRole: MobileRole): AuthSession {
  if (account.role !== expectedRole) {
    // Same user-facing behavior as before: credentials that authenticate
    // successfully but belong to the wrong portal are still rejected,
    // rather than silently logging the person in as the wrong role.
    throw new Error(
      expectedRole === 'USER' ? 'Incorrect username or password.' : 'Incorrect Worker ID or password.'
    );
  }
  return toSession(account);
}

/** Wraps ApiError/NetworkUnavailableError into the plain, user-facing Error screens already expect. */
function toUserFacingError(err: unknown, invalidCredentialsMessage: string): Error {
  if (err instanceof ApiError) {
    if (err.status === 401) {
      return new Error(invalidCredentialsMessage);
    }
    return new Error(err.message);
  }
  if (err instanceof NetworkUnavailableError) {
    return err;
  }
  return err instanceof Error ? err : new Error('Login failed.');
}

async function loginWithBackend(username: string, password: string, expectedRole: MobileRole): Promise<AuthSession> {
  let raw: RawLoginResponse;
  try {
    raw = await request<RawLoginResponse>('/auth/login', {
      method: 'POST',
      body: { login_id: username, password },
    });
  } catch (err) {
    throw toUserFacingError(
      err,
      expectedRole === 'USER' ? 'Incorrect username or password.' : 'Incorrect Worker ID or password.'
    );
  }

  const session = sessionFromAccount(raw.account, expectedRole);
  await SecureStore.setItemAsync(TOKEN_KEY, raw.access_token);
  return session;
}

export async function loginAsUser(username: string, password: string): Promise<AuthSession> {
  return loginWithBackend(username, password, 'USER');
}

export async function loginAsWorker(username: string, password: string): Promise<AuthSession> {
  return loginWithBackend(username, password, 'WORKER');
}

// The backend has no signup endpoint at all (`POST /auth/login` and
// `GET /auth/me` are the only two auth routes — see
// `backend/app/api/auth.py`). Real user signup is out of scope for
// Phase 6A (auth-foundation only) and cannot be added on the client
// side without a backend change, which this phase's scope requires
// stopping and asking about rather than adding silently. `signUpAsUser`
// therefore remains the pre-existing local/mock implementation from
// Phase 2, unchanged, so the existing Sign Up screen keeps working in
// the prototype sense it always has.
interface MockAccountRecord {
  username: string;
  password: string;
  displayName: string;
}

const mockUserAccounts: MockAccountRecord[] = [];

function simulateNetworkDelay<T>(value: T): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), 300));
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

// Deliberately no signUpAsWorker export: workers do not self-register.

/**
 * Attempts to reconstruct a session from a previously persisted token by
 * calling `GET /auth/me`. Returns `null` if there is no session to
 * restore right now — but whether the persisted token itself is cleared
 * depends on *why* the call failed, since those are different
 * situations (Phase 6A correction):
 *
 * - 401 (invalid/expired token, or an account the backend has since
 *   deactivated): the token really is dead — clear it.
 * - The account is real but isn't a USER/WORKER account: this token
 *   will never work for this client — clear it.
 * - The backend is unreachable (`NetworkUnavailableError`): says
 *   nothing about whether the token is valid — keep it, so the user
 *   isn't logged out just because they opened the app offline. The UI
 *   simply stays logged out until the next restore attempt (app
 *   restart) succeeds; retrying automatically within the same session
 *   is a later phase's concern.
 * - Any other API error (e.g. a 500): doesn't establish that the token
 *   itself is invalid either — keep it, for the same reason.
 */
export async function restoreSession(): Promise<AuthSession | null> {
  const token = await SecureStore.getItemAsync(TOKEN_KEY);
  if (!token) {
    return null;
  }

  try {
    const account = await request<RawAccount>('/auth/me', { token });
    return toSession(account);
  } catch (err) {
    if (err instanceof ApiError && err.status === 401) {
      await SecureStore.deleteItemAsync(TOKEN_KEY);
      return null;
    }
    if (err instanceof WrongAccountTypeError) {
      await SecureStore.deleteItemAsync(TOKEN_KEY);
      return null;
    }
    // NetworkUnavailableError, or any other API error that doesn't
    // establish the token itself is invalid: keep the token.
    return null;
  }
}

/** The persisted access token, if any — for future authenticated requests. */
export async function getAccessToken(): Promise<string | null> {
  return SecureStore.getItemAsync(TOKEN_KEY);
}

export async function logout(): Promise<void> {
  await SecureStore.deleteItemAsync(TOKEN_KEY);
}
