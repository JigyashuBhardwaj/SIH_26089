/**
 * Payment for a completed booking. The user pays the federation, not the
 * worker directly (see project payment model). MVP uses a QR-based flow;
 * this type is intentionally narrow so a real gateway can be added later
 * without a breaking shape change.
 */
export type PaymentMethod = 'QR';

export type PaymentStatus = 'PENDING' | 'PAID' | 'FAILED';

export interface Payment {
  id: string;
  bookingId: string;
  amount: number;
  method: PaymentMethod;
  status: PaymentStatus;
  paidAt?: string;
}
