import { useNavigate } from 'react-router-dom';
import { KarmanyaLogo } from '../components/KarmanyaLogo';
import styles from './PortalSelectionPage.module.css';

/**
 * The first thing anyone sees when opening the admin web app. Replaces
 * the old single generic login page as the entry point — there is no
 * longer a third "just log in" path visible anywhere in the UI, only the
 * choice between the two dedicated portals.
 */
export function PortalSelectionPage() {
  const navigate = useNavigate();

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <div className={styles.brandRow}>
          <KarmanyaLogo size="large" />
        </div>
        <h1 className={styles.title}>Welcome to Karmanya</h1>
        <p className={styles.subtitle}>Choose the portal you want to access</p>

        <div className={styles.options}>
          <button type="button" className={styles.portalCard} onClick={() => navigate('/login/federation')}>
            <span className={styles.portalTitle}>Federation Portal</span>
            <span className={styles.portalDescription}>Manage associations and oversee federation operations.</span>
          </button>

          <button
            type="button"
            className={`${styles.portalCard} ${styles.portalCardGreen}`}
            onClick={() => navigate('/login/association')}
          >
            <span className={styles.portalTitle}>Association Portal</span>
            <span className={styles.portalDescription}>Manage workers and service operations.</span>
          </button>
        </div>
      </div>
    </div>
  );
}
