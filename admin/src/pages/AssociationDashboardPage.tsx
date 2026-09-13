import { DashboardLayout } from '../components/DashboardLayout';
import { SummaryCard } from '../components/SummaryCard';
import { useAuth } from '../features/auth';
import styles from './AssociationDashboardPage.module.css';

/**
 * Shown only to ASSOCIATION_ADMIN accounts. Everything displayed comes
 * from the logged-in demo account, never a URL param — so an association
 * admin can never end up viewing another association's dashboard by
 * guessing a URL. Values are static demo/placeholder data; there is no
 * backend or request database yet (Phase 5+).
 */
export function AssociationDashboardPage() {
  const { account } = useAuth();

  if (!account || account.role !== 'ASSOCIATION_ADMIN') {
    return null;
  }

  return (
    <DashboardLayout>
      <p className={styles.eyebrow}>Welcome back</p>
      <h1 className={styles.title}>{account.associationName}</h1>

      <div className={styles.gridHeader}>
        <span className={styles.demoBadge}>Demo data</span>
      </div>
      <div className={styles.grid}>
        <SummaryCard label="New Requests" value="3" />
        <SummaryCard label="Active Jobs" value="5" accent="green" />
        <SummaryCard label="Workers" value={account.workerCount} />
        <SummaryCard label="Current Workload" value="Moderate" accent="green" />
      </div>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Recent Activity</h2>
        <div className={styles.emptyCard}>
          <p className={styles.emptyText}>No activity yet. This will populate once request management is live.</p>
        </div>
      </section>
    </DashboardLayout>
  );
}
