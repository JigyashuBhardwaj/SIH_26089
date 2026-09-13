import { DashboardLayout } from '../components/DashboardLayout';
import styles from './ComingSoonPage.module.css';

interface ComingSoonPageProps {
  title: string;
}

/**
 * Shown for every nav item that isn't built yet (Requests, Workers,
 * Associations, Analytics). Same wording style as the mobile app's
 * ComingSoonDialog — this is a normal, expected state, not an error.
 */
export function ComingSoonPage({ title }: ComingSoonPageProps) {
  return (
    <DashboardLayout>
      <div className={styles.wrap}>
        <h1 className={styles.pageTitle}>{title}</h1>
        <div className={styles.card}>
          <span className={styles.emoji} aria-hidden="true">
            🚀
          </span>
          <h2 className={styles.title}>Coming Soon</h2>
          <p className={styles.body}>This feature will be available in a future update.</p>
        </div>
      </div>
    </DashboardLayout>
  );
}
