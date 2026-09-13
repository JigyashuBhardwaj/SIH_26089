import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { ComingSoonModal } from '../components/ComingSoonModal';
import { KarmanyaLogo } from '../components/KarmanyaLogo';
import { useAuth } from '../features/auth';
import styles from './LoginPage.module.css';

export function LoginPage() {
  const navigate = useNavigate();
  const { login } = useAuth();

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
      login(loginId.trim(), password);
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
        <p className={styles.subtitle}>Association &amp; Federation Portal</p>

        <form className={styles.form} onSubmit={handleSubmit}>
          <label className={styles.field}>
            <span className={styles.fieldLabel}>Association / Admin ID</span>
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

          <button
            type="button"
            className={styles.forgotPasswordLink}
            onClick={() => setComingSoonOpen(true)}
          >
            Forgot Password?
          </button>

          {error ? <p className={styles.error}>{error}</p> : null}

          <button type="submit" className={styles.submitButton}>
            Login
          </button>

          <button
            type="button"
            className={styles.registerFederationLink}
            onClick={() => setComingSoonOpen(true)}
          >
            Register as a Federation
          </button>
        </form>

        <div className={styles.demoHint}>
          <p className={styles.demoHintTitle}>Demo accounts</p>
          <p>dhanbad_skilled / skilled123</p>
          <p>dhanbad_general / general123</p>
          <p>federation_admin / federation123</p>
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
