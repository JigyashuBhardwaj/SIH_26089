import { useState } from 'react';
import { ComingSoonModal } from '../components/ComingSoonModal';
import { DashboardLayout } from '../components/DashboardLayout';
import { getAllAssociations } from '../data/demoAccounts';
import { useAuth } from '../features/auth';
import { ComingSoonPage } from './ComingSoonPage';
import styles from './AssociationsPage.module.css';

/**
 * Federation-only overview of both demo associations. Association Admins
 * never see this route in their sidebar (see DashboardLayout), and if one
 * navigates here directly by URL, they get the same Coming Soon fallback
 * as any other not-yet-built section rather than federation-level
 * association-management information.
 *
 * This is a read-only overview + Coming Soon management actions — no
 * create/edit/delete/credential logic exists here.
 */
export function AssociationsPage() {
  const { account } = useAuth();
  const [comingSoonOpen, setComingSoonOpen] = useState(false);

  if (account?.role !== 'FEDERATION_ADMIN') {
    return <ComingSoonPage title="Associations" />;
  }

  const associations = getAllAssociations();

  return (
    <DashboardLayout>
      <div className={styles.headerRow}>
        <div>
          <h1 className={styles.title}>Associations</h1>
          <p className={styles.subtitle}>Federation-level overview of both demo associations.</p>
        </div>
        <button type="button" className={styles.primaryButton} onClick={() => setComingSoonOpen(true)}>
          + Add a New Association
        </button>
      </div>

      <div className={styles.list}>
        {associations.map((association) => (
          <div key={association.associationId} className={styles.card}>
            <div className={styles.cardHeader}>
              <div>
                <h2 className={styles.cardTitle}>{association.associationName}</h2>
                <p className={styles.cardMeta}>
                  {association.associationId} · {association.location}
                </p>
              </div>
              <span className={styles.ratingBadge}>★ {association.rating.toFixed(1)}</span>
            </div>

            <div className={styles.detailGrid}>
              <div className={styles.detailItem}>
                <span className={styles.detailLabel}>Workers</span>
                <span className={styles.detailValue}>{association.workerCount}</span>
              </div>
              <div className={styles.detailItem}>
                <span className={styles.detailLabel}>Coverage</span>
                <span className={styles.detailValue}>{association.coverage}</span>
              </div>
            </div>

            <div className={styles.servicesBlock}>
              <span className={styles.detailLabel}>Key Services</span>
              <div className={styles.chipRow}>
                {association.services.map((service) => (
                  <span key={service} className={styles.chip}>
                    {service}
                  </span>
                ))}
              </div>
            </div>

            <button type="button" className={styles.manageButton} onClick={() => setComingSoonOpen(true)}>
              Manage Association
            </button>
          </div>
        ))}
      </div>

      <p className={styles.disclaimer}>
        These are fictional demo associations for this prototype — not real-world organizations.
      </p>

      <ComingSoonModal open={comingSoonOpen} onClose={() => setComingSoonOpen(false)} />
    </DashboardLayout>
  );
}
