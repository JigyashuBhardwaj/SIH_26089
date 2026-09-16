import { getEffectiveAvailability, getEffectiveWorkload, type Worker } from '../data/workerCatalog';
import styles from './WorkerTable.module.css';

interface WorkerTableProps {
  workers: Worker[];
  showAssociationColumn: boolean;
  onSelectWorker: (workerId: string) => void;
}

const AVAILABILITY_BADGE_CLASS: Record<Worker['availabilityStatus'], string> = {
  Available: 'badgeGreen',
  Busy: 'badgeAmber',
  Unavailable: 'badgeGrey',
  'On Leave': 'badgeBlue',
};

export function WorkerTable({ workers, showAssociationColumn, onSelectWorker }: WorkerTableProps) {
  if (workers.length === 0) {
    return (
      <div className={styles.emptyState}>
        <p className={styles.emptyTitle}>No workers found</p>
        <p className={styles.emptyBody}>Try a different search term or adjust your filters.</p>
      </div>
    );
  }

  return (
    <div className={styles.tableWrap}>
      <table className={styles.table}>
        <thead>
          <tr>
            <th>Worker</th>
            {showAssociationColumn ? <th>Association</th> : null}
            <th>Skills</th>
            <th>Status</th>
            <th>Availability</th>
            <th>Current Workload</th>
            <th>Rating</th>
          </tr>
        </thead>
        <tbody>
          {workers.map((worker) => {
            const effectiveAvailability = getEffectiveAvailability(worker);
            return (
              <tr key={worker.workerId} className={styles.row} onClick={() => onSelectWorker(worker.workerId)}>
                <td>
                  <div className={styles.workerCell}>
                    <span className={styles.workerName}>{worker.fullName}</span>
                    <span className={styles.workerId}>{worker.workerId}</span>
                  </div>
                </td>
                {showAssociationColumn ? <td className={styles.associationCell}>{worker.associationName}</td> : null}
                <td className={styles.skillsCell}>{worker.skills.join(', ')}</td>
                <td>
                  <span className={`${styles.badge} ${styles[worker.workerStatus === 'Active' ? 'badgeGreen' : 'badgeGrey']}`}>
                    {worker.workerStatus}
                  </span>
                </td>
                <td>
                  <span className={`${styles.badge} ${styles[AVAILABILITY_BADGE_CLASS[effectiveAvailability]]}`}>
                    {effectiveAvailability}
                  </span>
                </td>
                <td>{getEffectiveWorkload(worker)}</td>
                <td>★ {worker.rating.toFixed(1)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
