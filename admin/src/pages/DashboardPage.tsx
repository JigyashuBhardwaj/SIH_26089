import { useAuth } from '../features/auth';
import { AssociationDashboardPage } from './AssociationDashboardPage';
import { FederationDashboardPage } from './FederationDashboardPage';

/**
 * The single "/dashboard" route renders different content purely based on
 * the logged-in account's role — never a URL param — so an association
 * admin has no way (not even by editing the URL) to view another
 * association's dashboard or the federation view.
 */
export function DashboardPage() {
  const { account } = useAuth();

  if (account?.role === 'FEDERATION_ADMIN') {
    return <FederationDashboardPage />;
  }

  if (account?.role === 'ASSOCIATION_ADMIN') {
    return <AssociationDashboardPage />;
  }

  return null;
}
