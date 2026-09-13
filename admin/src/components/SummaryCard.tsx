import styles from './SummaryCard.module.css';

interface SummaryCardProps {
  label: string;
  value: string;
  accent?: 'blue' | 'green';
}

/** A single demo/placeholder metric tile. Values are static demo data — no backend exists yet. */
export function SummaryCard({ label, value, accent = 'blue' }: SummaryCardProps) {
  return (
    <div className={styles.card}>
      <span className={`${styles.accentBar} ${accent === 'green' ? styles.accentGreen : styles.accentBlue}`} />
      <span className={styles.value}>{value}</span>
      <span className={styles.label}>{label}</span>
    </div>
  );
}
