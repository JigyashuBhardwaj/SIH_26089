import type { Role } from '@shared/auth';
import { ApiError, NetworkUnavailableError, request } from './apiClient';

export { ApiError, NetworkUnavailableError };

/**
 * Real backend authentication (Phase 6A).
 *
 * `POST /auth/login` and `GET /auth/me` are the only two endpoints this
 * phase integrates. See `mobile/services/authService.ts` for the same
 * pattern on the mobile side.
 *
 * Note: unlike every other backend response (which uses camelCase field
 * names via Pydantic aliases), `AccountPublic`/`LoginResponse`
 * (`backend/app/schemas/auth.py`) have no aliases at all, so the raw
 * wire response for these two endpoints uses snake_case field names
 * (`login_id`, `is_active`, `access_token`, ...). This file maps that
 * raw shape to a normalized camelCase `RealAccount` at the boundary,
 * rather than letting the inconsistency leak into the rest of the admin
 * app.
 */

export type AdminRole = Extract<Role, 'ASSOCIATION_ADMIN' | 'FEDERATION_ADMIN'>;

/**
 * The real, authenticated account identity — everything the backend
 * actually knows. `associationId`/`federationId` here are the
 * AUTHORITATIVE backend UUIDs (straight from `AccountPublic`) — not to
 * be confused with the unrelated, display-only `associationId` string
 * that `admin/src/data/demoAccounts.ts`/`AuthContext.tsx`'s
 * `toDisplayAccount` layer on top for the existing prototype UI; see
 * that function's docstring for the full ID-boundary explanation.
 */
export interface RealAccount {
  id: string;
  loginId: string;
  role: AdminRole;
  isActive: boolean;
  associationId: string | null;
  federationId: string | null;
}

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

function isAdminRole(role: Role): role is AdminRole {
  return role === 'ASSOCIATION_ADMIN' || role === 'FEDERATION_ADMIN';
}

/**
 * Thrown by `toRealAccount` when a token belongs to a real, valid
 * account that just isn't a Federation/Association account. Distinct
 * from `ApiError` so callers (see `AuthContext`'s session restoration)
 * can tell "this token will never work for this client" apart from "the
 * backend rejected/couldn't verify the token".
 */
export class WrongAccountTypeError extends Error {}

function toRealAccount(raw: RawAccount): RealAccount {
  if (!isAdminRole(raw.role)) {
    throw new WrongAccountTypeError('This account is not a Federation or Association account.');
  }
  return {
    id: raw.id,
    loginId: raw.login_id,
    role: raw.role,
    isActive: raw.is_active,
    associationId: raw.association_id,
    federationId: raw.federation_id,
  };
}

/** Wraps ApiError/NetworkUnavailableError into a plain, user-facing Error the login pages already expect. */
function toUserFacingError(err: unknown): Error {
  if (err instanceof ApiError) {
    // Uniform message, matching the pre-existing demo-account behavior:
    // never reveal *why* a login failed (unknown ID, wrong password, or
    // — new in Phase 6A — an inactive account, or the right credentials
    // typed into the wrong portal).
    if (err.status === 401) {
      return new Error('Invalid ID or password.');
    }
    return new Error(err.message);
  }
  if (err instanceof NetworkUnavailableError) {
    return err;
  }
  return err instanceof Error ? err : new Error('Login failed.');
}

interface LoginResult {
  account: RealAccount;
  accessToken: string;
}

async function loginWithBackend(loginId: string, password: string, expectedRole: AdminRole): Promise<LoginResult> {
  let raw: RawLoginResponse;
  try {
    raw = await request<RawLoginResponse>('/auth/login', {
      method: 'POST',
      body: { login_id: loginId, password },
    });
  } catch (err) {
    throw toUserFacingError(err);
  }

  const account = toRealAccount(raw.account);
  if (account.role !== expectedRole) {
    // Same behavior as the old demo lookup: correct credentials typed
    // into the wrong portal (e.g. an Association ID/password on the
    // Federation Login page) are still rejected, not silently logged in
    // as the wrong portal.
    throw new Error('Invalid ID or password.');
  }

  return { account, accessToken: raw.access_token };
}

export async function loginFederation(loginId: string, password: string): Promise<LoginResult> {
  return loginWithBackend(loginId, password, 'FEDERATION_ADMIN');
}

export async function loginAssociation(loginId: string, password: string): Promise<LoginResult> {
  return loginWithBackend(loginId, password, 'ASSOCIATION_ADMIN');
}

/**
 * Reconstructs a session from a previously persisted token by calling
 * `GET /auth/me`. Throws (rather than returning null) on any failure —
 * the caller decides what "invalid token" means for restoring a session.
 */
export async function fetchCurrentAccount(token: string): Promise<RealAccount> {
  const raw = await request<RawAccount>('/auth/me', { token });
  return toRealAccount(raw);
}
