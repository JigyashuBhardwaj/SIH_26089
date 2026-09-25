import { Navigate, Route, Routes } from 'react-router-dom';
import { ProtectedRoute } from './components/ProtectedRoute';
import { DashboardPage } from './pages/DashboardPage';
import { AssociationLoginPage } from './pages/AssociationLoginPage';
import { AssociationsPage } from './pages/AssociationsPage';
import { ComingSoonPage } from './pages/ComingSoonPage';
import { FederationLoginPage } from './pages/FederationLoginPage';
import { PortalSelectionPage } from './pages/PortalSelectionPage';
import { RequestDetailPage } from './pages/RequestDetailPage';
import { RequestsPage } from './pages/RequestsPage';
import { WorkerDetailPage } from './pages/WorkerDetailPage';
import { WorkersPage } from './pages/WorkersPage';

/**
 * Phase 4C route map: Portal Selection is the entry point (`/`), branching
 * into two dedicated login routes rather than one generic login form.
 * Everything past login is unchanged from Phase 4A/4B.
 */
export default function App() {
  return (
    <Routes>
      <Route path="/" element={<PortalSelectionPage />} />
      <Route path="/login/federation" element={<FederationLoginPage />} />
      <Route path="/login/association" element={<AssociationLoginPage />} />

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
            <RequestsPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/requests/:requestId"
        element={
          <ProtectedRoute>
            <RequestDetailPage />
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
