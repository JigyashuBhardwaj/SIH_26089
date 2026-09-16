import type { AvailabilityStatus, WorkerFilterOptions, WorkerStatus } from '../data/workerCatalog';
import styles from './WorkerFilters.module.css';

interface AssociationOption {
  associationId: string;
  associationName: string;
}

interface WorkerFiltersProps {
  query: string;
  onQueryChange: (query: string) => void;
  filters: WorkerFilterOptions;
  onFiltersChange: (filters: WorkerFilterOptions) => void;
  skillOptions: string[];
  associationOptions?: AssociationOption[];
}

const AVAILABILITY_OPTIONS: AvailabilityStatus[] = ['Available', 'Busy', 'Unavailable', 'On Leave'];
const WORKER_STATUS_OPTIONS: WorkerStatus[] = ['Active', 'Inactive'];
const WORKLOAD_OPTIONS: { value: NonNullable<WorkerFilterOptions['workloadBucket']>; label: string }[] = [
  { value: 'none', label: 'None (0)' },
  { value: 'light', label: 'Light (1-2)' },
  { value: 'high', label: 'High (3-4)' },
  { value: 'heavy', label: 'Heavy (5+)' },
];

export function WorkerFilters({
  query,
  onQueryChange,
  filters,
  onFiltersChange,
  skillOptions,
  associationOptions,
}: WorkerFiltersProps) {
  return (
    <div className={styles.wrap}>
      <input
        className={styles.search}
        type="text"
        placeholder="Search by name, worker ID, or phone number..."
        value={query}
        onChange={(event) => onQueryChange(event.target.value)}
      />

      <div className={styles.selects}>
        {associationOptions ? (
          <select
            className={styles.select}
            value={filters.associationId ?? ''}
            onChange={(event) => onFiltersChange({ ...filters, associationId: event.target.value || undefined })}
          >
            <option value="">All Associations</option>
            {associationOptions.map((option) => (
              <option key={option.associationId} value={option.associationId}>
                {option.associationName}
              </option>
            ))}
          </select>
        ) : null}

        <select
          className={styles.select}
          value={filters.skill ?? ''}
          onChange={(event) => onFiltersChange({ ...filters, skill: event.target.value || undefined })}
        >
          <option value="">All Skills</option>
          {skillOptions.map((skill) => (
            <option key={skill} value={skill}>
              {skill}
            </option>
          ))}
        </select>

        <select
          className={styles.select}
          value={filters.availabilityStatus ?? ''}
          onChange={(event) =>
            onFiltersChange({ ...filters, availabilityStatus: (event.target.value || undefined) as AvailabilityStatus | undefined })
          }
        >
          <option value="">All Availability</option>
          {AVAILABILITY_OPTIONS.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>

        <select
          className={styles.select}
          value={filters.workerStatus ?? ''}
          onChange={(event) =>
            onFiltersChange({ ...filters, workerStatus: (event.target.value || undefined) as WorkerStatus | undefined })
          }
        >
          <option value="">All Statuses</option>
          {WORKER_STATUS_OPTIONS.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>

        <select
          className={styles.select}
          value={filters.workloadBucket ?? ''}
          onChange={(event) =>
            onFiltersChange({
              ...filters,
              workloadBucket: (event.target.value || undefined) as WorkerFilterOptions['workloadBucket'],
            })
          }
        >
          <option value="">All Workloads</option>
          {WORKLOAD_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
