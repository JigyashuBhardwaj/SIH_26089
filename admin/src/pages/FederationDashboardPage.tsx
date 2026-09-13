import { useState } from 'react';
import { ComingSoonModal } from '../components/ComingSoonModal';
import { DashboardLayout } from '../components/DashboardLayout';
import { SummaryCard } from '../components/SummaryCard';
import { getAllAssociations } from '../data/demoAccounts';
import { useAuth } from '../features/auth';
import styles from './FederationDashboardPage.module.css';

/**
 * Shown only to FEDERATION_ADMIN. Unlike the association dashboard, this
 * one intentionally shows both demo associations at once — the
 * federation-level view oversees both. Values are static demo/placeholder
 * data; there is no backend or association database yet.
 */
export function FederationDashboardPage() {
  const { account } = useAuth();
  const associations = getAllAssociations();
  const [comingSoonOpen, setComingSoonOpen] = useState(false);

  if (!account || account.role !== 'FEDERATION_ADMIN') {
    return null;
  }

  return (
    <DashboardLayout>
      <p className={styles.eyebrow}>Welcome back</p>
      <h1 className={styles.title}>{account.name}</h1>

      <div className={styles.gridHeader}>
        <span className={styles.demoBadge}>Demo data</span>
      </div>
      <div className={styles.grid}>
        <SummaryCard label="Total Associations" value={String(associations.length)} />
        <SummaryCard label="Total Workers" value="215+" accent="green" />
        <SummaryCard label="Active Requests" value="8" />
        <SummaryCard label="Active Jobs" value="12" accent="green" />
      </div>

      <section className={styles.section}>
        <div className={styles.sectionHeaderRow}>
          <h2 className={styles.sectionTitle}>Associations Overview</h2>
          <button type="button" className={styles.addAssociationButton} onClick={() => setComingSoonOpen(true)}>
            + Add a New Association
          </button>
        </div>
        <div className={styles.associationList}>
          {associations.map((association) => (
            <div key={association.associationId} className={styles.associationCard}>
              <div className={styles.associationHeader}>
                <span className={styles.associationName}>{association.associationName}</span>
                <span className={styles.workerBadge}>{association.workerCount} workers</span>
              </div>
              <p className={styles.associationServices}>{association.services.join(' • ')}</p>
            </div>
          ))}
        </div>
      </section>

      <ComingSoonModal open={comingSoonOpen} onClose={() => setComingSoonOpen(false)} />
    </DashboardLayout>
  );
}
