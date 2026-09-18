import { PortalLoginForm } from '../components/PortalLoginForm';
import { useAuth } from '../features/auth';

export function FederationLoginPage() {
  const { loginFederation } = useAuth();

  return (
    <PortalLoginForm
      portalTitle="Federation Portal"
      idFieldLabel="Federation ID"
      demoHint="federation_admin / federation123"
      onLogin={loginFederation}
      showRegisterLink
    />
  );
}
