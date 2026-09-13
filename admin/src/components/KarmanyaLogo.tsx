import styles from './KarmanyaLogo.module.css';

interface KarmanyaLogoProps {
  /** 'large' for a prominent placement (login card), 'compact' for header use. */
  size?: 'large' | 'compact';
  showTagline?: boolean;
}

/**
 * Reproduces the mobile app's KarmanyaLogo (mobile/components/KarmanyaLogo.tsx):
 * two overlapping person-silhouette marks (green, rotated -8deg; blue,
 * rotated +8deg) above the "KARMANYA" wordmark. The mobile version is
 * built from two Ionicons "body" glyphs rather than an image asset, so
 * there's no bitmap to copy — this reproduces the same composition with
 * a small inline SVG silhouette instead of pulling in an icon library.
 */
export function KarmanyaLogo({ size = 'compact', showTagline = false }: KarmanyaLogoProps) {
  const isLarge = size === 'large';
  const iconSize = isLarge ? 44 : 28;

  return (
    <div className={styles.container}>
      <div className={styles.markRow}>
        <PersonMark size={iconSize} color="var(--color-green)" className={styles.markLeft} />
        <PersonMark size={iconSize} color="var(--color-action-blue)" className={styles.markRight} />
      </div>
      <span className={`${styles.title} ${isLarge ? styles.titleLarge : ''}`}>KARMANYA</span>
      {showTagline ? <span className={styles.tagline}>People · Work · Stronger Communities</span> : null}
    </div>
  );
}

function PersonMark({ size, color, className }: { size: number; color: string; className: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className} aria-hidden="true">
      <circle cx="12" cy="6.5" r="3.5" fill={color} />
      <path
        d="M4 21c0-4.5 3.5-8 8-8s8 3.5 8 8"
        stroke={color}
        strokeWidth="3"
        strokeLinecap="round"
        fill="none"
      />
    </svg>
  );
}
