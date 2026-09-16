import { useNavigate, useParams } from 'react-router-dom';
import { DashboardLayout } from '../components/DashboardLayout';
import { getEffectiveAssignments, getEffectiveAvailability, getEffectiveWorkload, getTodayISODate, getWorkerById } from '../data/workerCatalog';
import { useAuth } from '../features/auth';
import styles from './WorkerDetailPage.module.css';

/**
 * Read-only worker profile. No edit, allocation, or leave-approval
 * controls — this phase is display-only. Association admins can only
 * reach a worker's profile via their own scoped Workers list (the route
 * itself doesn't re-check association ownership beyond that, since
 * there's no way to reach an out-of-scope workerId from the UI without
 * typing a URL directly — handled below by simply not finding a
 * federation-only visible worker for the wrong association account).
 */
export function WorkerDetailPage() {
  const { workerId } = useParams<{ workerId: string }>();
  const { account } = useAuth();
  const navigate = useNavigate();

  const worker = workerId ? getWorkerById(workerId) : undefined;

  // Association admins must not be able to view another association's
  // worker profile even by editing the URL directly.
  const isAuthorized =
    account?.role === 'FEDERATION_ADMIN' ||
    (account?.role === 'ASSOCIATION_ADMIN' && worker?.associationId === account.associationId);

  if (!account) return null;

  if (!worker || !isAuthorized) {
    return (
      <DashboardLayout>
        <button type="button" className={styles.backButton} onClick={() => navigate('/workers')}>
          ← Back to Workers
        </button>
        <div className={styles.notFoundCard}>
          <p className={styles.notFoundTitle}>Worker not found</p>
          <p className={styles.notFoundBody}>
            This worker doesn&apos;t exist or isn&apos;t part of your association.
          </p>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <button type="button" className={styles.backButton} onClick={() => navigate('/workers')}>
        ← Back to Workers
      </button>

      <div className={styles.headerCard}>
        <div>
          <h1 className={styles.name}>{worker.fullName}</h1>
          <p className={styles.workerId}>{worker.workerId}</p>
        </div>
        <span className={`${styles.statusBadge} ${worker.workerStatus === 'Active' ? styles.badgeGreen : styles.badgeGrey}`}>
          {worker.workerStatus}
        </span>
      </div>

      <div className={styles.grid}>
        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>Identity</h2>
          <dl className={styles.fieldList}>
            <div className={styles.field}>
              <dt>Full Name</dt>
              <dd>{worker.fullName}</dd>
            </div>
            <div className={styles.field}>
              <dt>Worker ID</dt>
              <dd>{worker.workerId}</dd>
            </div>
            <div className={styles.field}>
              <dt>Association</dt>
              <dd>{worker.associationName}</dd>
            </div>
            <div className={styles.field}>
              <dt>Worker Status</dt>
              <dd>{worker.workerStatus}</dd>
            </div>
          </dl>
        </section>

        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>Contact &amp; Location</h2>
          <dl className={styles.fieldList}>
            <div className={styles.field}>
              <dt>Phone Number</dt>
              <dd>{worker.phoneNumber}</dd>
            </div>
            <div className={styles.field}>
              <dt>Address</dt>
              <dd>{worker.address}</dd>
            </div>
            <div className={styles.field}>
              <dt>PIN Code</dt>
              <dd>{worker.pincode}</dd>
            </div>
          </dl>
        </section>

        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>Skills</h2>
          <div className={styles.chipRow}>
            {worker.skills.map((skill) => (
              <span key={skill} className={styles.chip}>
                {skill}
              </span>
            ))}
          </div>
        </section>

        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>Performance</h2>
          <dl className={styles.fieldList}>
            <div className={styles.field}>
              <dt>Rating</dt>
              <dd>★ {worker.rating.toFixed(1)}</dd>
            </div>
            <div className={styles.field}>
              <dt>Total Jobs Completed</dt>
              <dd>{worker.totalJobsCompleted}</dd>
            </div>
          </dl>
        </section>

        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>Availability</h2>
          <dl className={styles.fieldList}>
            <div className={styles.field}>
              <dt>Current Availability</dt>
              <dd>{getEffectiveAvailability(worker)}</dd>
            </div>
            <div className={styles.field}>
              <dt>Current Workload</dt>
              <dd>{getEffectiveWorkload(worker)}</dd>
            </div>
          </dl>
        </section>

        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>Upcoming Leave</h2>
          {worker.upcomingLeave && worker.upcomingLeave.endDate >= getTodayISODate() ? (
            <dl className={styles.fieldList}>
              <div className={styles.field}>
                <dt>Start Date</dt>
                <dd>{worker.upcomingLeave.startDate}</dd>
              </div>
              <div className={styles.field}>
                <dt>End Date</dt>
                <dd>{worker.upcomingLeave.endDate}</dd>
              </div>
              <div className={styles.field}>
                <dt>Status</dt>
                <dd>{worker.upcomingLeave.status}</dd>
              </div>
            </dl>
          ) : (
            <p className={styles.emptyText}>No upcoming leave</p>
          )}
        </section>
      </div>

      <section className={styles.sectionFull}>
        <h2 className={styles.sectionTitle}>Current Assignments</h2>
        {(() => {
          const effectiveAssignments = getEffectiveAssignments(worker);
          return effectiveAssignments.length > 0 ? (
            <div className={styles.assignmentsTableWrap}>
              <table className={styles.assignmentsTable}>
                <thead>
                  <tr>
                    <th>Request ID</th>
                    <th>Service</th>
                    <th>Scheduled Date</th>
                    <th>Scheduled Time</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {effectiveAssignments.map((assignment) => (
                    <tr key={assignment.requestId}>
                      <td>{assignment.requestId}</td>
                      <td>{assignment.service}</td>
                      <td>{assignment.scheduledDate}</td>
                      <td>{assignment.scheduledTime}</td>
                      <td>{assignment.status}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className={styles.emptyText}>No current assignments</p>
          );
        })()}
      </section>
    </DashboardLayout>
  );
}
