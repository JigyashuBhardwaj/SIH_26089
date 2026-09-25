import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import type { ServiceRequest } from '@shared/types/booking';
import { DashboardLayout } from '../components/DashboardLayout';
import { useAuth } from '../features/auth';
import {
  buildServiceNameMap,
  describeFetchError,
  fetchOwnAssociationRequests,
  fetchServiceCatalogue,
} from '../services/associationRequestsService';
import styles from './RequestsPage.module.css';

type LoadState = 'loading' | 'error' | 'ready';

function formatRequestedDateTime(iso: string): string {
  const parsed = new Date(iso);
  if (Number.isNaN(parsed.getTime())) {
    return iso;
  }
  return parsed.toLocaleString(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  });
}

/**
 * Phase 6C: Association Admin's own request list, backed by the real
 * `GET /associations/me/requests` and `GET /services` endpoints. Backend
 * authoritative throughout — no locally fabricated status/ordering.
 *
 * Role-gated the same way `AssociationDashboardPage.tsx` is, rather than
 * by modifying `DashboardLayout.tsx`'s nav (a Federation Admin still sees
 * "Requests" in the sidebar, but landing here renders nothing for them).
 */
export function RequestsPage() {
  const { account } = useAuth();
  const navigate = useNavigate();

  const [loadState, setLoadState] = useState<LoadState>('loading');
  const [loadError, setLoadError] = useState<string | null>(null);
  const [requests, setRequests] = useState<ServiceRequest[]>([]);
  const [serviceNames, setServiceNames] = useState<Map<string, string>>(new Map());

  const load = useCallback(async () => {
    setLoadState('loading');
    setLoadError(null);
    try {
      const [ownRequests, services] = await Promise.all([fetchOwnAssociationRequests(), fetchServiceCatalogue()]);
      setRequests(ownRequests);
      setServiceNames(buildServiceNameMap(services));
      setLoadState('ready');
    } catch (err) {
      setLoadError(describeFetchError(err));
      setLoadState('error');
    }
  }, []);

  useEffect(() => {
    if (account?.role === 'ASSOCIATION_ADMIN') {
      load();
    }
  }, [account, load]);

  if (!account || account.role !== 'ASSOCIATION_ADMIN') {
    return null;
  }

  return (
    <DashboardLayout>
      <h1 className={styles.title}>Requests</h1>
      <p className={styles.subtitle}>Service requests submitted to {account.associationName}.</p>

      {loadState === 'loading' ? <p className={styles.stateText}>Loading requests…</p> : null}

      {loadState === 'error' ? (
        <div className={styles.errorCard}>
          <p className={styles.errorText}>{loadError}</p>
          <button type="button" className={styles.retryButton} onClick={load}>
            Retry
          </button>
        </div>
      ) : null}

      {loadState === 'ready' && requests.length === 0 ? (
        <div className={styles.emptyCard}>
          <p className={styles.emptyText}>No requests yet</p>
        </div>
      ) : null}

      {loadState === 'ready' && requests.length > 0 ? (
        <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Service</th>
                <th>Request Code</th>
                <th>Requested Date/Time</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {requests.map((req) => (
                <tr key={req.id} className={styles.row}>
                  <td>{serviceNames.get(req.serviceId) ?? 'Unknown service'}</td>
                  <td className={styles.requestCode}>{req.requestCode}</td>
                  <td>{formatRequestedDateTime(req.requestedDateTime)}</td>
                  <td>
                    <span className={styles.statusBadge}>{req.status}</span>
                  </td>
                  <td>
                    <button type="button" className={styles.viewButton} onClick={() => navigate(`/requests/${req.id}`)}>
                      View
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </DashboardLayout>
  );
}
