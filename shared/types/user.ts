/**
 * A person who books services through the mobile app's User flow.
 */
export interface User {
  id: string;
  name: string;
  phoneNumber: string;
  address?: string;
}
