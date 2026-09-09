import React, { createContext, useCallback, useContext, useMemo, useState } from 'react';
import * as authService from '../../services/authService';
import type { AuthSession } from '../../services/authService';

interface AuthContextValue {
  /** Null when nobody is logged in. */
  session: AuthSession | null;
  isAuthenticating: boolean;
  loginAsUser: (username: string, password: string) => Promise<void>;
  signUpAsUser: (params: { fullName: string; username: string; password: string }) => Promise<void>;
  loginAsWorker: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

/**
 * Provides mock auth state to the whole app. This is the only piece of
 * global state introduced for Phase 2 — plain React Context, no external
 * state-management library, as instructed.
 *
 * Session is held in memory only and is lost on app reload; there is no
 * backend or device storage yet to persist it against.
 */
export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<AuthSession | null>(null);
  const [isAuthenticating, setIsAuthenticating] = useState(false);

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
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({ session, isAuthenticating, loginAsUser, signUpAsUser, loginAsWorker, logout }),
    [session, isAuthenticating, loginAsUser, signUpAsUser, loginAsWorker, logout]
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
