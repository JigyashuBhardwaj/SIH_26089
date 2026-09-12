/**
 * Booking validation rules.
 *
 * These are referenced by both the mobile app (for immediate UI feedback,
 * e.g. disabling an invalid time slot) and the backend (as the source of
 * truth for what it will actually accept). Only the constants and function
 * signatures are established here — implementations land in Phase 3
 * (User App) and Phase 4 (Backend), not in this foundation step.
 */

/** A requested service time must be at least this many hours after booking time. */
export const MIN_BOOKING_LEAD_TIME_HOURS = 4;

/** A user can cancel free of charge until this many hours before service time. */
export const FREE_CANCELLATION_WINDOW_HOURS = 2;

/**
 * Whether a requested service time satisfies the minimum lead time.
 * `bookingTime` is when the request is being made (normally `new Date()`);
 * `requestedServiceTime` is the date/time the person picked. The boundary
 * is inclusive: exactly MIN_BOOKING_LEAD_TIME_HOURS from now is valid.
 */
export function isServiceTimeValid(bookingTime: Date, requestedServiceTime: Date): boolean {
  const minValidTime = bookingTime.getTime() + MIN_BOOKING_LEAD_TIME_HOURS * 60 * 60 * 1000;
  return requestedServiceTime.getTime() >= minValidTime;
}

/**
 * Whether a booking can still be cancelled free of charge.
 * Not implemented yet — see FREE_CANCELLATION_WINDOW_HOURS.
 */
export function isFreeCancellationWindowOpen(_serviceTime: Date, _now: Date): boolean {
  throw new Error('isFreeCancellationWindowOpen is not implemented yet (Phase 3/7).');
}
