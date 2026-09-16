import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ComingSoonModal } from '../components/ComingSoonModal';
import { DashboardLayout } from '../components/DashboardLayout';
import { WorkerFilters } from '../components/WorkerFilters';
import { WorkerTable } from '../components/WorkerTable';
import { getAllAssociations } from '../data/demoAccounts';
import { searchAndFilterWorkers, WORKERS, getWorkersByAssociation, type WorkerFilterOptions } from '../data/workerCatalog';
import { useAuth } from '../features/auth';
import styles from './WorkersPage.module.css';

/**
 * Read-only worker directory. Association admins only ever see their own
 * association's workers (scoped before any search/filter runs, so there
 * is no code path that could leak another association's data). Federation
 * sees all 215 with an Association column/filter, and is strictly
 * read-only here — "Leave Requests" and "+ Add a Worker" only render for
 * Association Admin, since those represent an association managing its
 * own workers, not something the federation does. No allocation, edit,
 * availability-change, or leave-approval controls exist anywhere here —
 * that's explicitly out of scope for this phase.
 */
export function WorkersPage() {
  const { account } = useAuth();
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [filters, setFilters] = useState<WorkerFilterOptions>({});
  const [comingSoonOpen, setComingSoonOpen] = useState(false);

  const isFederation = account?.role === 'FEDERATION_ADMIN';

  // Scoped to the logged-in association BEFORE search/filter ever runs.
  const baseWorkers = useMemo(() => {
    if (isFederation) return WORKERS;
    if (account?.role === 'ASSOCIATION_ADMIN') return getWorkersByAssociation(account.associationId);
    return [];
  }, [isFederation, account]);

  const skillOptions = useMemo(
    () => Array.from(new Set(baseWorkers.flatMap((worker) => worker.skills))).sort(),
    [baseWorkers]
  );

  const associationOptions = useMemo(
    () =>
      isFederation
        ? getAllAssociations().map((a) => ({ associationId: a.associationId, associationName: a.associationName }))
        : undefined,
    [isFederation]
  );

  const results = useMemo(
    () => searchAndFilterWorkers(baseWorkers, query, filters),
    [baseWorkers, query, filters]
  );

  if (!account) return null;

  return (
    <DashboardLayout>
      <div className={styles.headerRow}>
        <div>
          <h1 className={styles.title}>Workers</h1>
          <p className={styles.subtitle}>
            {isFederation
              ? `${baseWorkers.length} workers across both associations`
              : `${baseWorkers.length} workers in your association`}
          </p>
        </div>
        <div className={styles.actions}>
          {!isFederation ? (
            <>
              <button type="button" className={styles.secondaryButton} onClick={() => setComingSoonOpen(true)}>
                Leave Requests
              </button>
              <button type="button" className={styles.primaryButton} onClick={() => setComingSoonOpen(true)}>
                + Add a Worker
              </button>
            </>
          ) : null}
        </div>
      </div>

      <WorkerFilters
        query={query}
        onQueryChange={setQuery}
        filters={filters}
        onFiltersChange={setFilters}
        skillOptions={skillOptions}
        associationOptions={associationOptions}
      />

      <p className={styles.resultCount}>
        {results.length} {results.length === 1 ? 'result' : 'results'}
      </p>

      <WorkerTable
        workers={results}
        showAssociationColumn={isFederation}
        onSelectWorker={(workerId) => navigate(`/workers/${workerId}`)}
      />

      <ComingSoonModal open={comingSoonOpen} onClose={() => setComingSoonOpen(false)} />
    </DashboardLayout>
  );
}
