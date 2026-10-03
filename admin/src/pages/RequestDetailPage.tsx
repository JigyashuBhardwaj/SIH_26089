import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import type { ServiceRequest } from '@shared/types/booking';
import { DashboardLayout } from '../components/DashboardLayout';
import { useAuth } from '../features/auth';
import {
  ApiError,
  type Candidate,
  buildServiceNameMap,
  createAssignment,
  describeAssignError,
  describeCandidatesError,
  describeFetchError,
  fetchCandidates,
  fetchOwnAssociationRequest,
  fetchServiceCatalogue,
} from '../services/associationRequestsService';
import styles from './RequestDetailPage.module.css';

type LoadState = 'loading' | 'error' | 'ready';
type CandidateState = 'idle' | 'loading' | 'error' | 'ready';

const FINDABLE_STATUSES = new Set(['PENDING', 'MATCHING']);

/** Phase 6G: how often this page silently re-fetches the request in the background. */
const POLL_INTERVAL_MS = 5000;

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
 * Phase 6C: single ServiceRequest detail for an Association Admin, backed
 * by `GET /associations/me/requests/{requestId}`, candidate discovery
 * (`GET .../candidates`), and manual assignment
 * (`POST .../assignments`). Every mutating action re-fetches the request
 * afterward and renders that response as ground truth — nothing here
 * locally infers or fabricates a status.
 */
export function RequestDetailPage() {
  const { account } = useAuth();
  const { requestId } = useParams<{ requestId: string }>();
  const navigate = useNavigate();

  const [loadState, setLoadState] = useState<LoadState>('loading');
  const [loadError, setLoadError] = useState<string | null>(null);
  const [serviceRequest, setServiceRequest] = useState<ServiceRequest | null>(null);
  const [serviceNames, setServiceNames] = useState<Map<string, string>>(new Map());

  const [candidateState, setCandidateState] = useState<CandidateState>('idle');
  const [candidateError, setCandidateError] = useState<string | null>(null);
  const [candidates, setCandidates] = useState<Candidate[]>([]);

  const [assigningWorkerId, setAssigningWorkerId] = useState<string | null>(null);
  const [assignError, setAssignError] = useState<string | null>(null);

  const loadRequest = useCallback(async () => {
    if (!requestId) return;
    setLoadState('loading');
    setLoadError(null);
    try {
      const [req, services] = await Promise.all([fetchOwnAssociationRequest(requestId), fetchServiceCatalogue()]);
      setServiceRequest(req);
      setServiceNames(buildServiceNameMap(services));
      setLoadState('ready');
    } catch (err) {
      setLoadError(describeFetchError(err));
      setLoadState('error');
    }
  }, [requestId]);

  useEffect(() => {
    if (account?.role === 'ASSOCIATION_ADMIN') {
      loadRequest();
    }
  }, [account, loadRequest]);

  // Phase 6G: background-refresh this request while the admin is viewing
  // it, so a worker accepting/declining/cancelling/completing it
  // elsewhere shows up here without the admin having to navigate away and
  // back (the only thing that currently re-fetches, since React Router
  // happens to remount this page on route change). Calls only
  // `fetchOwnAssociationRequest` — the service catalogue rarely changes
  // and re-fetching it every tick would be wasted work, so each poll tick
  // writes straight to `serviceRequest` without touching `serviceNames`,
  // `loadState`, or `loadError`; `loadRequest` above (mount + after
  // `handleAssign`) remains the only place that fetches the service
  // catalogue. A poll tick never flips this page into its "Loading
  // request…" state and a poll failure never replaces it with the full
  // error card — the next scheduled tick (or the admin's own Retry/
  // mutation) simply tries again. Mount-scoped: stops entirely on
  // unmount (the admin navigates away). A tick is skipped — never
  // queued — while a previous tick is still in flight, while the admin's
  // own `handleAssign` mutation is running, or while the
  // initial/own-mutation `loadRequest` call above is already loading, so
  // polling can never overlap itself or race an explicit mutation.
  const assigningWorkerIdRef = useRef(assigningWorkerId);
  assigningWorkerIdRef.current = assigningWorkerId;
  const loadStateRef = useRef(loadState);
  loadStateRef.current = loadState;

  useEffect(() => {
    if (account?.role !== 'ASSOCIATION_ADMIN' || !requestId) {
      return;
    }

    let isTickInFlight = false;

    const intervalId = window.setInterval(() => {
      if (isTickInFlight || assigningWorkerIdRef.current !== null || loadStateRef.current === 'loading') {
        return;
      }
      isTickInFlight = true;
      fetchOwnAssociationRequest(requestId)
        .then((req) => {
          setServiceRequest(req);
        })
        .catch(() => {
          // Silent by design — see this effect's doc comment above.
        })
        .finally(() => {
          isTickInFlight = false;
        });
    }, POLL_INTERVAL_MS);

    return () => window.clearInterval(intervalId);
  }, [account, requestId]);

  const handleFindCandidates = useCallback(async () => {
    if (!requestId) return;
    setCandidateState('loading');
    setCandidateError(null);
    try {
      const results = await fetchCandidates(requestId);
      setCandidates(results);
      setCandidateState('ready');
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        // The request is no longer PENDING/MATCHING — re-fetch it and
        // show its current authoritative state instead of fabricating a
        // candidate list.
        setCandidateState('idle');
        setCandidates([]);
        await loadRequest();
        return;
      }
      setCandidateError(describeCandidatesError(err));
      setCandidateState('error');
    }
  }, [requestId, loadRequest]);

  const handleAssign = useCallback(
    async (workerId: string) => {
      if (!requestId) return;
      setAssigningWorkerId(workerId);
      setAssignError(null);
      try {
        await createAssignment(requestId, workerId);
        // Never locally infer ASSIGNED — re-fetch and treat that response
        // as authoritative, then clear the candidate list.
        await loadRequest();
        setCandidates([]);
        setCandidateState('idle');
      } catch (err) {
        if (err instanceof ApiError && err.status === 409) {
          setAssignError(err.message);
          await loadRequest();
        } else {
          setAssignError(describeAssignError(err));
        }
      } finally {
        setAssigningWorkerId(null);
      }
    },
    [requestId, loadRequest]
  );

  if (!account || account.role !== 'ASSOCIATION_ADMIN') {
    return null;
  }

  return (
    <DashboardLayout>
      <button type="button" className={styles.backLink} onClick={() => navigate('/requests')}>
        ← Back to Requests
      </button>

      {loadState === 'loading' ? <p className={styles.stateText}>Loading request…</p> : null}

      {loadState === 'error' ? (
        <div className={styles.errorCard}>
          <p className={styles.errorText}>{loadError}</p>
          <button type="button" className={styles.retryButton} onClick={loadRequest}>
            Retry
          </button>
        </div>
      ) : null}

      {loadState === 'ready' && serviceRequest ? (
        <>
          <h1 className={styles.title}>{serviceNames.get(serviceRequest.serviceId) ?? 'Unknown service'}</h1>
          <p className={styles.requestCode}>{serviceRequest.requestCode}</p>

          <div className={styles.detailCard}>
            <div className={styles.detailRow}>
              <span className={styles.detailLabel}>Status</span>
              <span className={styles.statusBadge}>{serviceRequest.status}</span>
            </div>
            <div className={styles.detailRow}>
              <span className={styles.detailLabel}>Requested Date/Time</span>
              <span>{formatRequestedDateTime(serviceRequest.requestedDateTime)}</span>
            </div>
            <div className={styles.detailRow}>
              <span className={styles.detailLabel}>Address</span>
              <span>{serviceRequest.address}</span>
            </div>
            <div className={styles.detailRow}>
              <span className={styles.detailLabel}>Pincode</span>
              <span>{serviceRequest.pincode}</span>
            </div>
          </div>

          {serviceRequest.status === 'ASSIGNED' ? (
            <div className={styles.infoCard}>
              <p className={styles.infoText}>
                This request has been assigned. Worker details are available via the assignment record.
              </p>
            </div>
          ) : null}

          {serviceRequest.status === 'CANCELLED_BY_USER' ? (
            <div className={styles.infoCard}>
              <p className={styles.infoText}>This request was cancelled by the user.</p>
            </div>
          ) : null}

          {serviceRequest.status === 'COMPLETED' ? (
            <div className={styles.infoCard}>
              <p className={styles.infoText}>This request has been completed.</p>
            </div>
          ) : null}

          {FINDABLE_STATUSES.has(serviceRequest.status) ? (
            <section className={styles.candidatesSection}>
              {candidateState === 'idle' ? (
                <button type="button" className={styles.primaryButton} onClick={handleFindCandidates}>
                  Find Candidates
                </button>
              ) : null}

              {candidateState === 'loading' ? <p className={styles.stateText}>Loading candidates…</p> : null}

              {candidateState === 'error' ? (
                <div className={styles.errorCard}>
                  <p className={styles.errorText}>{candidateError}</p>
                  <button type="button" className={styles.retryButton} onClick={handleFindCandidates}>
                    Retry
                  </button>
                </div>
              ) : null}

              {assignError ? <p className={styles.assignErrorText}>{assignError}</p> : null}

              {candidateState === 'ready' ? (
                candidates.length === 0 ? (
                  <div className={styles.emptyCard}>
                    <p className={styles.emptyText}>No eligible candidates found.</p>
                  </div>
                ) : (
                  <div className={styles.tableWrap}>
                    <table className={styles.table}>
                      <thead>
                        <tr>
                          <th>Worker</th>
                          <th>Phone</th>
                          <th>Rating</th>
                          <th>Jobs Completed</th>
                          <th>Active Assignments</th>
                          <th>Pincode</th>
                          <th></th>
                        </tr>
                      </thead>
                      <tbody>
                        {candidates.map((candidate) => (
                          <tr key={candidate.workerId} className={styles.row}>
                            <td>
                              <div className={styles.workerCell}>
                                <span className={styles.workerName}>
                                  {candidate.fullName}
                                  {candidate.previouslyDeclined ? (
                                    <span className={styles.previouslyDeclinedBadge}>Previously declined</span>
                                  ) : null}
                                </span>
                                <span className={styles.workerCode}>{candidate.workerCode}</span>
                              </div>
                            </td>
                            <td>{candidate.phoneNumber ?? '—'}</td>
                            <td>★ {candidate.rating.toFixed(2)}</td>
                            <td>{candidate.totalJobsCompleted}</td>
                            <td>{candidate.activeAssignmentCount}</td>
                            <td>
                              {candidate.pincode}
                              {candidate.samePincode ? <span className={styles.samePincodeBadge}>Same pincode</span> : null}
                            </td>
                            <td>
                              <button
                                type="button"
                                className={styles.assignButton}
                                disabled={assigningWorkerId !== null}
                                onClick={() => handleAssign(candidate.workerId)}
                              >
                                {assigningWorkerId === candidate.workerId ? 'Assigning…' : 'Assign'}
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )
              ) : null}
            </section>
          ) : null}
        </>
      ) : null}
    </DashboardLayout>
  );
}
