import { PortalLoginForm } from '../components/PortalLoginForm';
import { useAuth } from '../features/auth';

export function AssociationLoginPage() {
  const { loginAssociation } = useAuth();

  return (
    <PortalLoginForm
      portalTitle="Association Portal"
      idFieldLabel="Association ID"
      demoHint="dhanbad_skilled / skilled123 · dhanbad_general / general123"
      onLogin={loginAssociation}
    />
  );
}
