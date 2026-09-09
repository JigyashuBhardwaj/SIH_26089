/**
 * A cooperative labour association (or federation) that verifies workers
 * and operates the Admin Dashboard.
 */
export interface Association {
  id: string;
  name: string;
  federationId?: string;
  pinCodesServed: string[];
}
