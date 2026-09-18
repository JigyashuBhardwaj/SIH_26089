import type { ReactNode } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../features/auth';

/** Redirects to the portal selection screen if nobody is logged in. */
export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { account } = useAuth();

  if (!account) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}
