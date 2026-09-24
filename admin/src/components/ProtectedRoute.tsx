import type { ReactNode } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../features/auth';

/**
 * Redirects to the portal selection screen if nobody is logged in.
 *
 * Phase 6A: a session can now be persisted (see `AuthContext`) and is
 * validated against the backend on app start, which is not instant. If
 * this component redirected on `!account` immediately, reloading the
 * page on a protected route would always bounce to `/` before that
 * restoration finished, defeating the point of persisting the token —
 * so it renders nothing until `isRestoringSession` settles.
 */
export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { account, isRestoringSession } = useAuth();

  if (isRestoringSession) {
    return null;
  }

  if (!account) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}
