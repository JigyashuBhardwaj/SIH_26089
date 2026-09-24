import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import {
  getAssociationDisplayByLoginId,
  getFederationDisplayByLoginId,
  type DemoAccount,
} from '../../data/demoAccounts';
import * as authService from '../../services/authService';
import { ApiError, WrongAccountTypeError } from '../../services/authService';
import type { RealAccount } from '../../services/authService';

interface AuthContextValue {
  account: DemoAccount | null;
  /** True while a persisted token is being validated against the backend on app start. */
  isRestoringSession: boolean;
  /** Rejects with a user-facing message if the ID/password don't match a Federation account. */
  loginFederation: (loginId: string, password: string) => Promise<void>;
  /** Rejects with a user-facing message if the ID/password don't match an Association account. */
  loginAssociation: (loginId: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

const TOKEN_STORAGE_KEY = 'karmanya_admin_access_token';

/**
 * Builds the `DemoAccount`-shaped object the existing dashboard/worker
 * pages already consume (`account.associationName`, `account.workerCount`,
 * `account.name`, `account.associationId`, ...) from a REAL, authenticated
 * backend account plus static display metadata.
 *
 * Phase 6A design note (flagged explicitly, not a silent decision): the
 * real backend `Account`/`Association` models don't carry these display
 * fields at all (no rating, worker count, coverage, or association/
 * federation display name — see `backend/app/schemas/association.py`
 * and `backend/app/schemas/auth.py`), and wiring up the endpoints that
 * *would* supply adjacent real data (e.g. `GET /federation/me/associations`)
 * is out of scope for this auth-foundation-only phase. So the display
 * fields are resolved from the same static demo catalogue the UI always
 * used, keyed by the real account's `loginId` — which works today
 * because the backend's Phase 5F seed data and this static catalogue
 * describe the same demo dataset by construction. A real account whose
 * `loginId` isn't in that catalogue (a genuine future non-demo account)
 * gets safe placeholder display values instead of crashing.
 *
 * ID BOUNDARY (Phase 6A correction — made explicit, not implied):
 * `account.associationId`/`account.federationId` (on the `RealAccount`
 * parameter below, straight from the backend's `AccountPublic`) are the
 * AUTHORITATIVE backend identifiers — real UUIDs, the ones any future
 * real API call must use. The `associationId` placed on the returned
 * `DemoAccount` below is a DIFFERENT, UNRELATED value: it comes from the
 * static local demo catalogue (`admin/src/data/demoAccounts.ts`, e.g.
 * `'dhanbad_skilled'`) and exists only so
 * `admin/src/data/workerCatalog.ts`'s `getWorkersByAssociation()` —
 * which is keyed by that same local/display format, not a UUID — keeps
 * working. It is display/prototype data only and must never be read as
 * if it were `account.associationId`. This mapping is a stand-in for
 * Phase 6A (auth only); it will be replaced once a later Phase 6
 * sub-phase connects the Admin UI to real association APIs (at which
 * point `getWorkersByAssociation`/`workerCatalog.ts` will key off the
 * real backend UUID instead, and this static lookup can go away). Not
 * resolved here — see the Phase 6 inspection report's identity-format
 * finding.
 */
function toDisplayAccount(account: RealAccount): DemoAccount {
  if (account.role === 'FEDERATION_ADMIN') {
    const display = getFederationDisplayByLoginId(account.loginId);
    return {
      role: 'FEDERATION_ADMIN',
      loginId: account.loginId,
      name: display?.name ?? account.loginId,
    };
  }

  const display = getAssociationDisplayByLoginId(account.loginId);
  return {
    role: 'ASSOCIATION_ADMIN',
    loginId: account.loginId,
    // DISPLAY/PROTOTYPE id, in the local demo-catalogue format — NOT
    // `account.associationId` (the real backend UUID). See the ID
    // BOUNDARY note in this function's docstring above.
    associationId: display?.associationId ?? account.loginId,
    associationName: display?.associationName ?? account.loginId,
    services: display?.services ?? [],
    workerCount: display?.workerCount ?? '—',
    location: display?.location ?? '—',
    rating: display?.rating ?? 0,
    coverage: display?.coverage ?? '—',
  };
}

/**
 * Holds the current admin session. Plain React Context, no external
 * state library — unchanged since Phase 4C.
 *
 * Phase 6A: `loginFederation`/`loginAssociation` now authenticate
 * against the real backend (`services/authService.ts`) instead of the
 * static demo account list, and the resulting JWT is persisted to
 * `localStorage` so a session survives a page reload — the old
 * "refreshing the page returns to the portal selection screen" behavior
 * is gone, replaced by restoring the session from that token via
 * `GET /auth/me` on app start.
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [account, setAccount] = useState<DemoAccount | null>(null);
  // Initialized directly from whether a token exists, rather than always
  // starting true and setting it false in the effect below when there's
  // nothing to restore — avoids a synchronous setState-in-effect call
  // for that branch.
  const [isRestoringSession, setIsRestoringSession] = useState(() => Boolean(localStorage.getItem(TOKEN_STORAGE_KEY)));

  useEffect(() => {
    let cancelled = false;

    const token = localStorage.getItem(TOKEN_STORAGE_KEY);
    if (!token) {
      return;
    }

    authService
      .fetchCurrentAccount(token)
      .then((real) => {
        if (!cancelled) {
          setAccount(toDisplayAccount(real));
        }
      })
      .catch((err) => {
        // Phase 6A correction: only clear the persisted token when the
        // response actually establishes that the token itself is
        // invalid — a 401 (expired/invalid/inactive-account), or a real
        // account that just isn't a Federation/Association account (it
        // will never work for this client either way). A backend that's
        // merely unreachable, or any other API error, says nothing
        // about whether the token is still good, so the credential is
        // kept — the UI simply stays logged out until a future
        // retry/session-restoration mechanism (a later phase) can try
        // again, rather than throwing away a possibly-valid session.
        if ((err instanceof ApiError && err.status === 401) || err instanceof WrongAccountTypeError) {
          localStorage.removeItem(TOKEN_STORAGE_KEY);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setIsRestoringSession(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const loginFederation = useCallback(async (loginId: string, password: string) => {
    const { account: real, accessToken } = await authService.loginFederation(loginId, password);
    localStorage.setItem(TOKEN_STORAGE_KEY, accessToken);
    setAccount(toDisplayAccount(real));
  }, []);

  const loginAssociation = useCallback(async (loginId: string, password: string) => {
    const { account: real, accessToken } = await authService.loginAssociation(loginId, password);
    localStorage.setItem(TOKEN_STORAGE_KEY, accessToken);
    setAccount(toDisplayAccount(real));
  }, []);

  const logout = useCallback(() => {
    setAccount(null);
    localStorage.removeItem(TOKEN_STORAGE_KEY);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({ account, isRestoringSession, loginFederation, loginAssociation, logout }),
    [account, isRestoringSession, loginFederation, loginAssociation, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

/** Access the current admin session. Must be used under AuthProvider. */
export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider.');
  }
  return context;
}
