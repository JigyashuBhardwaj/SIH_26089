/**
 * Worker matching / assignment criteria.
 *
 * The transparent scoring/ranking algorithm (availability + geographic
 * proximity/PIN code + work balance) is implemented in Phase 5 alongside
 * the Admin Dashboard. Only the shape of the criteria and the function
 * signature are established here, so the Admin Dashboard and backend can
 * agree on a contract before either is built. This is deliberately NOT
 * an AI/ML model — it stays a deterministic, inspectable algorithm.
 */
import type { Worker, Booking } from '../types';

export interface MatchingCriteria {
  availability: boolean;
  pinCodeProximityScore: number;
  workBalanceScore: number;
}

/**
 * Ranks candidate workers for a booking, best match first.
 * Not implemented yet — see Phase 5.
 */
export function rankCandidateWorkers(_booking: Booking, _candidates: Worker[]): Worker[] {
  throw new Error('rankCandidateWorkers is not implemented yet (Phase 5).');
}
