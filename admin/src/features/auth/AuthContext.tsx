import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react';
import { findAccount, type DemoAccount } from '../../data/demoAccounts';

interface AuthContextValue {
  account: DemoAccount | null;
  /** Throws with a user-facing message on invalid credentials. */
  login: (loginId: string, password: string) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

/**
 * Holds the current demo admin session. Plain React Context, no external
 * state library — same reasoning as the mobile app's AuthProvider. There
 * is no backend yet, so the session lives only in memory for the current
 * browser tab/session; refreshing the page returns to the login screen.
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [account, setAccount] = useState<DemoAccount | null>(null);

  const login = useCallback((loginId: string, password: string) => {
    setAccount(findAccount(loginId, password));
  }, []);

  const logout = useCallback(() => {
    setAccount(null);
  }, []);

  const value = useMemo<AuthContextValue>(() => ({ account, login, logout }), [account, login, logout]);

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
