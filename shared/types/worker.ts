/**
 * A worker verified and onboarded by a labour association/federation.
 * Workers do not self-register — credentials are issued by an admin
 * (see Admin Dashboard, Phase 5).
 */
export interface Worker {
  id: string;
  name: string;
  phoneNumber: string;
  associationId: string;
  skills: string[];
  pinCode: string;
  isAvailable: boolean;
}
