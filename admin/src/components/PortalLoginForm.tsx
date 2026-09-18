import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { ComingSoonModal } from './ComingSoonModal';
import { KarmanyaLogo } from './KarmanyaLogo';
import styles from './PortalLoginForm.module.css';

interface PortalLoginFormProps {
  portalTitle: string;
  idFieldLabel: string;
  demoHint: string;
  /** Throws with a user-facing message on invalid credentials. */
  onLogin: (loginId: string, password: string) => void;
  showRegisterLink?: boolean;
}

/**
 * The shared visual/behavioral shell for both dedicated login pages
 * (Federation and Association): logo, portal title, ID + password fields
 * (with the existing show/hide eye), Forgot Password, Login, an optional
 * Register link, and a back-to-portal-selection link. Only the field
 * label, portal title, demo hint text, login handler, and whether the
 * register link appears differ between the two pages.
 */
export function PortalLoginForm({ portalTitle, idFieldLabel, demoHint, onLogin, showRegisterLink }: PortalLoginFormProps) {
  const navigate = useNavigate();

  const [loginId, setLoginId] = useState('');
  const [password, setPassword] = useState('');
  const [passwordVisible, setPasswordVisible] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [comingSoonOpen, setComingSoonOpen] = useState(false);

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    setError(null);

    if (!loginId.trim() || !password) {
      setError('Please enter both an ID and a password.');
      return;
    }

    try {
      onLogin(loginId.trim(), password);
      navigate('/dashboard', { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Invalid ID or password.');
    }
  };

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <div className={styles.brandRow}>
          <KarmanyaLogo size="large" />
        </div>
        <p className={styles.subtitle}>{portalTitle}</p>

        <form className={styles.form} onSubmit={handleSubmit}>
          <label className={styles.field}>
            <span className={styles.fieldLabel}>{idFieldLabel}</span>
            <input
              className={styles.input}
              type="text"
              autoComplete="username"
              value={loginId}
              onChange={(event) => setLoginId(event.target.value)}
            />
          </label>

          <label className={styles.field}>
            <span className={styles.fieldLabel}>Password</span>
            <div className={styles.passwordWrap}>
              <input
                className={styles.input}
                type={passwordVisible ? 'text' : 'password'}
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
              <button
                type="button"
                className={styles.eyeButton}
                onClick={() => setPasswordVisible((visible) => !visible)}
                aria-label={passwordVisible ? 'Hide password' : 'Show password'}
                title={passwordVisible ? 'Hide password' : 'Show password'}
              >
                <EyeIcon crossedOut={passwordVisible} />
              </button>
            </div>
          </label>

          <button type="button" className={styles.forgotPasswordLink} onClick={() => setComingSoonOpen(true)}>
            Forgot Password?
          </button>

          {error ? <p className={styles.error}>{error}</p> : null}

          <button type="submit" className={styles.submitButton}>
            Login
          </button>

          {showRegisterLink ? (
            <button type="button" className={styles.secondaryLink} onClick={() => setComingSoonOpen(true)}>
              Register as a Federation
            </button>
          ) : null}
        </form>

        <button type="button" className={styles.backLink} onClick={() => navigate('/')}>
          ← Back to portal selection
        </button>

        <div className={styles.demoHint}>
          <p className={styles.demoHintTitle}>Demo account</p>
          <p>{demoHint}</p>
        </div>
      </div>

      <ComingSoonModal open={comingSoonOpen} onClose={() => setComingSoonOpen(false)} />
    </div>
  );
}

/** Simple inline eye / eye-with-slash icon — no icon library needed. */
function EyeIcon({ crossedOut }: { crossedOut: boolean }) {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M1.5 12S5 5 12 5s10.5 7 10.5 7-3.5 7-10.5 7S1.5 12 1.5 12Z"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinejoin="round"
      />
      <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="1.8" />
      {crossedOut ? <line x1="3" y1="21" x2="21" y2="3" stroke="currentColor" strokeWidth="1.8" /> : null}
    </svg>
  );
}
