import type { ReactNode } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { KarmanyaLogo } from './KarmanyaLogo';
import { useAuth } from '../features/auth';
import styles from './DashboardLayout.module.css';

interface DashboardLayoutProps {
  children: ReactNode;
}

interface NavItem {
  to: string;
  label: string;
  end?: boolean;
}

const BASE_NAV_ITEMS: NavItem[] = [
  { to: '/dashboard', label: 'Dashboard', end: true },
  { to: '/requests', label: 'Requests' },
  { to: '/workers', label: 'Workers' },
  { to: '/associations', label: 'Associations' },
  { to: '/analytics', label: 'Analytics' },
];

/**
 * The persistent header + sidebar shell for every logged-in screen. Only
 * "Dashboard" and "Workers" are functional so far — the rest render a
 * Coming Soon page (see ComingSoonPage.tsx), but they're real routes/nav
 * items so the URL and back button behave sensibly.
 *
 * "Associations" is federation-only: an Association Admin represents a
 * single association, so a cross-association management view doesn't
 * apply to them and is hidden from their sidebar entirely (not just
 * disabled) — see the filter below.
 */
export function DashboardLayout({ children }: DashboardLayoutProps) {
  const { account, logout } = useAuth();
  const navigate = useNavigate();

  const identityName =
    account?.role === 'FEDERATION_ADMIN' ? account.name : (account?.associationName ?? 'Karmanya Admin');
  const identityRoleLabel = account?.role === 'FEDERATION_ADMIN' ? 'Federation Admin' : 'Association Admin';

  const navItems =
    account?.role === 'ASSOCIATION_ADMIN' ? BASE_NAV_ITEMS.filter((item) => item.to !== '/associations') : BASE_NAV_ITEMS;

  const handleLogout = () => {
    logout();
    navigate('/', { replace: true });
  };

  return (
    <div className={styles.shell}>
      <header className={styles.topbar}>
        <div className={styles.brand}>
          <KarmanyaLogo size="compact" />
        </div>

        <div className={styles.profile}>
          <div className={styles.profileText}>
            <span className={styles.profileName}>{identityName}</span>
            <span className={styles.profileRole}>{identityRoleLabel}</span>
          </div>
          <button type="button" className={styles.logoutButton} onClick={handleLogout}>
            Logout
          </button>
        </div>
      </header>

      <div className={styles.body}>
        <nav className={styles.sidebar}>
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) => `${styles.navItem} ${isActive ? styles.navItemActive : ''}`}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        <main className={styles.content}>{children}</main>
      </div>
    </div>
  );
}
