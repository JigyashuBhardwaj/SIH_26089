import type { Role } from '../auth/roles';

/**
 * Phase 6A: the authenticated identity returned by the real backend's
 * `POST /auth/login` and `GET /auth/me` (`AccountPublic` in
 * `backend/app/schemas/auth.py`). This is the account/login row itself
 * — never a person's profile data (no name, no display fields); those
 * live on the separate `UserProfile`/`Worker` records and are not part
 * of this response. Never includes `password_hash`.
 */
export interface AuthAccount {
  id: string;
  loginId: string;
  role: Role;
  isActive: boolean;
  associationId: string | null;
  federationId: string | null;
  createdAt: string;
  updatedAt: string;
}

/** `POST /auth/login` response shape. */
export interface LoginResponse {
  accessToken: string;
  tokenType: string;
  account: AuthAccount;
}
