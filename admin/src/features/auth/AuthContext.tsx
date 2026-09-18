import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react';
import { findAssociationAccount, findFederationAccount, type DemoAccount } from '../../data/demoAccounts';

interface AuthContextValue {
  account: DemoAccount | null;
  /** Throws with a user-facing message if the ID/password don't match a Federation account. */
  loginFederation: (loginId: string, password: string) => void;
  /** Throws with a user-facing message if the ID/password don't match an Association account. */
  loginAssociation: (loginId: string, password: string) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

/**
 * Holds the current demo admin session. Plain React Context, no external
 * state library — same reasoning as the mobile app's AuthProvider. There
 * is no backend yet, so the session lives only in memory for the current
 * browser tab/session; refreshing the page returns to the portal
 * selection screen.
 *
 * Login is split into two role-scoped functions (rather than one generic
 * `login`) because Phase 4C gives Federation and Association each their
 * own dedicated login page: a correct Association ID/password typed on
 * the Federation Login page must still be rejected, not silently logged
 * in as the wrong portal.
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [account, setAccount] = useState<DemoAccount | null>(null);

  const loginFederation = useCallback((loginId: string, password: string) => {
    setAccount(findFederationAccount(loginId, password));
  }, []);

  const loginAssociation = useCallback((loginId: string, password: string) => {
    setAccount(findAssociationAccount(loginId, password));
  }, []);

  const logout = useCallback(() => {
    setAccount(null);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({ account, loginFederation, loginAssociation, logout }),
    [account, loginFederation, loginAssociation, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

/** Access the current demo admin session. Must be used under AuthProvider. */
export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider.');
  }
  return context;
}
