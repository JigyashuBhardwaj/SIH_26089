import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import * as authService from '../../services/authService';
import type { AuthSession } from '../../services/authService';

interface AuthContextValue {
  /** Null when nobody is logged in. */
  session: AuthSession | null;
  isAuthenticating: boolean;
  /** True while attempting to restore a session from a persisted token on app start. */
  isRestoringSession: boolean;
  loginAsUser: (username: string, password: string) => Promise<void>;
  signUpAsUser: (params: { fullName: string; username: string; password: string }) => Promise<void>;
  loginAsWorker: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

/**
 * Provides auth state to the whole app. Plain React Context, no external
 * state-management library — unchanged since Phase 2.
 *
 * Phase 6A: `authService` now calls the real backend and persists the
 * access token in SecureStore, so on app start this provider attempts to
 * restore a session from that token (`GET /auth/me`) before rendering
 * the role-selection screen, rather than always starting logged out.
 */
export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<AuthSession | null>(null);
  const [isAuthenticating, setIsAuthenticating] = useState(false);
  const [isRestoringSession, setIsRestoringSession] = useState(true);

  useEffect(() => {
    let cancelled = false;
    authService.restoreSession().then((restored) => {
      if (!cancelled) {
        setSession(restored);
        setIsRestoringSession(false);
      }
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const loginAsUser = useCallback(async (username: string, password: string) => {
    setIsAuthenticating(true);
    try {
      setSession(await authService.loginAsUser(username, password));
    } finally {
      setIsAuthenticating(false);
    }
  }, []);

  const signUpAsUser = useCallback(
    async (params: { fullName: string; username: string; password: string }) => {
      setIsAuthenticating(true);
      try {
        setSession(await authService.signUpAsUser(params));
      } finally {
        setIsAuthenticating(false);
      }
    },
    []
  );

  const loginAsWorker = useCallback(async (username: string, password: string) => {
    setIsAuthenticating(true);
    try {
      setSession(await authService.loginAsWorker(username, password));
    } finally {
      setIsAuthenticating(false);
    }
  }, []);

  const logout = useCallback(() => {
    setSession(null);
    // Fire-and-forget: clearing the persisted token doesn't need to
    // block the UI from returning to the logged-out state immediately.
    void authService.logout();
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({ session, isAuthenticating, isRestoringSession, loginAsUser, signUpAsUser, loginAsWorker, logout }),
    [session, isAuthenticating, isRestoringSession, loginAsUser, signUpAsUser, loginAsWorker, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

/** Access the current auth session and actions. Must be used under AuthProvider. */
export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider.');
  }
  return context;
}
