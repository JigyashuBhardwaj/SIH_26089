import styles from './ComingSoonModal.module.css';

interface ComingSoonModalProps {
  open: boolean;
  onClose: () => void;
}

/**
 * The same "Coming Soon" wording used on the sidebar's ComingSoonPage,
 * shown as an overlay instead of a full page navigation — for actions
 * that don't correspond to a nav destination (Forgot Password, Add a New
 * Association).
 */
export function ComingSoonModal({ open, onClose }: ComingSoonModalProps) {
  if (!open) return null;

  return (
    <div className={styles.backdrop} onClick={onClose}>
      <div className={styles.card} role="dialog" aria-modal="true" onClick={(event) => event.stopPropagation()}>
        <span className={styles.emoji} aria-hidden="true">
          🚀
        </span>
        <h2 className={styles.title}>Coming Soon</h2>
        <p className={styles.body}>This feature will be available in a future update.</p>
        <button type="button" className={styles.dismissButton} onClick={onClose}>
          Got it
        </button>
      </div>
    </div>
  );
}
