import { Navigate, Route, Routes } from 'react-router-dom';
import { ProtectedRoute } from './components/ProtectedRoute';
import { DashboardPage } from './pages/DashboardPage';
import { AssociationsPage } from './pages/AssociationsPage';
import { ComingSoonPage } from './pages/ComingSoonPage';
import { LoginPage } from './pages/LoginPage';
import { WorkerDetailPage } from './pages/WorkerDetailPage';
import { WorkersPage } from './pages/WorkersPage';

/**
 * Phase 4A route map: login + one protected dashboard route (role-based
 * content, see DashboardPage) + four Coming Soon placeholders for the
 * nav items that aren't built yet. Everything else falls back to login.
 */
export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LoginPage />} />

      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <DashboardPage />
          </ProtectedRoute>
        }
      />

      <Route
        path="/requests"
        element={
          <ProtectedRoute>
            <ComingSoonPage title="Requests" />
          </ProtectedRoute>
        }
      />
      <Route
        path="/workers"
        element={
          <ProtectedRoute>
            <WorkersPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/workers/:workerId"
        element={
          <ProtectedRoute>
            <WorkerDetailPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/associations"
        element={
          <ProtectedRoute>
            <AssociationsPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/analytics"
        element={
          <ProtectedRoute>
            <ComingSoonPage title="Analytics" />
          </ProtectedRoute>
        }
      />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
