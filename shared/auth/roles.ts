/**
 * Every role in the system. The mobile app only ever authenticates USER or
 * WORKER sessions; the Admin Dashboard authenticates ASSOCIATION_ADMIN and
 * FEDERATION_ADMIN sessions. Enforcement is the backend's responsibility —
 * this type just gives every part of the system a shared vocabulary.
 */
export type Role = 'USER' | 'WORKER' | 'ASSOCIATION_ADMIN' | 'FEDERATION_ADMIN';
