import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { useEffect, useState } from 'react';
import { ActivityIndicator, Pressable, RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';
import { BottomNavBar } from '../../components/BottomNavBar';
import { ConfirmDialog } from '../../components/ConfirmDialog';
import { ScreenHeader } from '../../components/ScreenHeader';
import { useAuth } from '../../features/auth';
import { useRequests, type LocalServiceRequest } from '../../features/requests';
import { ApiError, NetworkUnavailableError } from '../../services/apiClient';
import { colors, radius, spacing, typography } from '../../constants/theme';

/**
 * Request statuses the backend still allows the user to cancel from
 * (`_USER_CANCELLABLE_STATUSES` in `backend/app/api/requests.py`). Used
 * to decide whether the Cancel button/"active" styling shows, and — as
 * of Phase 6B-6 — matches the same set the backend enforces server-side
 * for the real `POST /requests/{id}/cancel` call this screen now makes.
 */
const CANCELLABLE_STATUSES: LocalServiceRequest['status'][] = ['PENDING', 'MATCHING', 'ASSIGNED', 'ACCEPTED'];

/**
 * Phase 6E-B: a visual "tone" for the status badge, independent of the
 * exact label text — keeps the badge styling small and reusable rather
 * than one bespoke style per status.
 */
type StatusTone = 'active' | 'attention' | 'success' | 'cancelled';

/**
 * Phase 6E-B: a complete label/tone for every `ServiceRequestStatus`
 * value, replacing the old binary "Finding a Worker"/"Cancelled"
 * presentation. Covers all 10 backend-defined statuses so this mapping
 * is exhaustive and never falls through to a default — but two of them
 * (`USER_CONFIRMED`, `PAID`) are included only for completeness: per
 * `backend/app/api/requests.py`'s `confirm_request_completion`/
 * `pay_for_request` docstrings, the backend conceptually passes a
 * request through those two statuses but never actually persists either
 * one (it finishes at `PAYMENT_PENDING`/`COMPLETED` respectively in the
 * same transaction), so a real request is never observed in either
 * state here. This mapping does not change that backend behavior in any
 * way — it just means those two entries are effectively unreachable in
 * practice.
 */
const STATUS_DISPLAY: Record<LocalServiceRequest['status'], { label: string; tone: StatusTone }> = {
  PENDING: { label: 'Finding a Worker', tone: 'active' },
  MATCHING: { label: 'Finding a Worker', tone: 'active' },
  ASSIGNED: { label: 'Worker Assigned', tone: 'active' },
  ACCEPTED: { label: 'Worker Confirmed', tone: 'active' },
  WORKER_COMPLETED: { label: 'Awaiting Your Confirmation', tone: 'attention' },
  USER_CONFIRMED: { label: 'Confirmed', tone: 'attention' },
  PAYMENT_PENDING: { label: 'Payment Pending', tone: 'attention' },
  PAID: { label: 'Paid', tone: 'success' },
  COMPLETED: { label: 'Completed', tone: 'success' },
  CANCELLED_BY_USER: { label: 'Cancelled', tone: 'cancelled' },
};

/**
 * Turns a `cancelRequest` failure (that isn't the 409 "no longer
 * cancellable" case, which is reconciled via `loadRequests` instead)
 * into a safe, user-facing message — same pattern as
 * `describeSubmitError` in `confirm-request.tsx` and
 * `describeLoadRequestsError` in `RequestsContext.tsx`.
 */
function describeCancelError(err: unknown): string {
  if (err instanceof ApiError || err instanceof NetworkUnavailableError) {
    return err.message;
  }
  return 'Something went wrong while cancelling your request. Please try again.';
}

/** Turns a `confirmRequest` failure (other than a 409, reconciled via `loadRequests`) into a safe message. */
function describeConfirmError(err: unknown): string {
  if (err instanceof ApiError || err instanceof NetworkUnavailableError) {
    return err.message;
  }
  return 'Something went wrong while confirming this request. Please try again.';
}

/** Turns a `payRequest` failure (other than a 409, reconciled via `loadRequests`) into a safe message. */
function describePayError(err: unknown): string {
  if (err instanceof ApiError || err instanceof NetworkUnavailableError) {
    return err.message;
  }
  return 'Something went wrong while completing payment. Please try again.';
}

/**
 * Reachable from User Home. Lists the authenticated user's real requests
 * from the backend (Phase 6B-5: `GET /requests`, via
 * `RequestsContext.loadRequests()` — this screen never fetches directly)
 * — both active ones ("Finding a Worker") and cancelled ones, kept
 * visible with a clear cancelled state rather than silently removed, so
 * the person still has a record of what they cancelled.
 */
export default function OngoingRequestsScreen() {
  const router = useRouter();
  const { session, logout } = useAuth();
  const { requests, loadState, loadError, loadRequests, cancelRequest, confirmRequest, payRequest } = useRequests();
  const [cancelTargetId, setCancelTargetId] = useState<string | null>(null);
  const [confirmTargetId, setConfirmTargetId] = useState<string | null>(null);
  const [payTargetId, setPayTargetId] = useState<string | null>(null);
  // Phase 6E-B: the one request currently being cancelled/confirmed/paid
  // (if any), across all three mutations — disables that specific card's
  // buttons so the same in-flight action can't be submitted twice, and
  // (since this is a single shared id, not one per action) also prevents
  // starting a second, different mutation on the same request while the
  // first is still in flight. Same "actioning id" pattern already used
  // by the Worker app's Booking Requests/Accepted Requests screens. Not
  // shared/context state: purely this screen's own transient UI concern.
  const [actioningId, setActioningId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  useEffect(() => {
    loadRequests();
  }, [loadRequests]);

  const handleLogout = () => {
    logout();
    router.replace('/role-selection');
  };

  const handleConfirmCancel = async () => {
    if (!cancelTargetId || actioningId) return;
    const targetId = cancelTargetId;
    setCancelTargetId(null);
    setActioningId(targetId);
    setActionError(null);

    try {
      await cancelRequest(targetId);
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        // Our local view of this request's status is stale — it's no
        // longer cancellable server-side (someone/something moved it
        // further along, or it was already cancelled). Don't fabricate a
        // status; reconcile with the backend instead. loadRequests()
        // never throws — on failure it sets its own loadState/loadError,
        // which the screen already renders (error card + Retry), so a
        // failed reconciliation surfaces as a real error rather than
        // being silently treated as success.
        await loadRequests();
      } else {
        setActionError(describeCancelError(err));
      }
    } finally {
      setActioningId(null);
    }
  };

  /**
   * Phase 6E-B: the user confirms the worker's completed job
   * (`POST /requests/{id}/confirm`). `confirmRequest` itself already
   * re-fetches the authoritative list on success (see
   * `RequestsContext.tsx`), so nothing here needs to patch `status`
   * locally — a 409 (request no longer WORKER_COMPLETED) is reconciled
   * the same way cancellation's is, via an explicit `loadRequests()`.
   */
  const handleConfirmCompletion = async () => {
    if (!confirmTargetId || actioningId) return;
    const targetId = confirmTargetId;
    setConfirmTargetId(null);
    setActioningId(targetId);
    setActionError(null);

    try {
      await confirmRequest(targetId);
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        await loadRequests();
      } else {
        setActionError(describeConfirmError(err));
      }
    } finally {
      setActioningId(null);
    }
  };

  /**
   * Phase 6E-B: the user completes the demo payment step
   * (`POST /requests/{id}/pay`) — same re-fetch-on-success,
   * reconcile-409-via-reload pattern as `handleConfirmCompletion` above.
   */
  const handleConfirmPayment = async () => {
    if (!payTargetId || actioningId) return;
    const targetId = payTargetId;
    setPayTargetId(null);
    setActioningId(targetId);
    setActionError(null);

    try {
      await payRequest(targetId);
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        await loadRequests();
      } else {
        setActionError(describePayError(err));
      }
    } finally {
      setActioningId(null);
    }
  };

  // A pull-to-refresh reload keeps the existing list visible while it
  // runs; only the very first load (nothing to show yet) uses the
  // full-screen loading state below.
  const isRefreshing = loadState === 'loading' && requests.length > 0;
  const isInitialLoading = loadState === 'loading' && requests.length === 0;

  return (
    <View style={styles.screen}>
      <View style={styles.headerWrap}>
        <ScreenHeader
          profileName={session?.displayName ?? 'User'}
          profileRoleLabel="User"
          onLogout={handleLogout}
        />
      </View>

      <ScrollView
        contentContainerStyle={styles.content}
        refreshControl={<RefreshControl refreshing={isRefreshing} onRefresh={loadRequests} />}
      >
        <Text style={styles.title}>Ongoing Requests</Text>
        <Text style={styles.subtitle}>Track and manage your service requests.</Text>

        {actionError ? (
          <View style={styles.errorCard}>
            <Ionicons name="close-circle-outline" size={18} color={colors.error} />
            <Text style={styles.errorCardText}>{actionError}</Text>
          </View>
        ) : null}

        {isInitialLoading ? (
          <View style={styles.centerState}>
            <ActivityIndicator color={colors.blue} />
            <Text style={styles.centerStateText}>Loading requests…</Text>
          </View>
        ) : loadState === 'error' ? (
          <View style={styles.centerState}>
            <Ionicons name="cloud-offline-outline" size={28} color={colors.textMuted} />
            <Text style={styles.emptyTitle}>Couldn&apos;t load requests</Text>
            <Text style={styles.emptyBody}>{loadError}</Text>
            <Pressable style={styles.retryButton} onPress={loadRequests}>
              <Text style={styles.retryButtonText}>Retry</Text>
            </Pressable>
          </View>
        ) : requests.length === 0 ? (
          <View style={styles.emptyState}>
            <Ionicons name="time-outline" size={32} color={colors.textMuted} />
            <Text style={styles.emptyTitle}>No requests yet</Text>
            <Text style={styles.emptyBody}>Book a service to see it here.</Text>
            <Pressable style={styles.emptyAction} onPress={() => router.push('/(user)/book-service')}>
              <Text style={styles.emptyActionText}>Book a Service</Text>
            </Pressable>
          </View>
        ) : (
          requests.map((request) => (
            <RequestCard
              key={request.requestId}
              request={request}
              isActioning={actioningId === request.requestId}
              onCancel={() => setCancelTargetId(request.requestId)}
              onConfirmCompletion={() => setConfirmTargetId(request.requestId)}
              onPay={() => setPayTargetId(request.requestId)}
            />
          ))
        )}
      </ScrollView>

      <BottomNavBar
        active="requests"
        onNavigateHome={() => router.replace('/(user)/home')}
        onNavigateRequests={() => {}}
      />

      <ConfirmDialog
        visible={cancelTargetId !== null}
        title="Cancel Request?"
        message="Are you sure you want to cancel this service request?"
        confirmLabel="Yes, Cancel Request"
        cancelLabel="Keep Request"
        destructive
        onConfirm={handleConfirmCancel}
        onCancel={() => setCancelTargetId(null)}
      />

      <ConfirmDialog
        visible={confirmTargetId !== null}
        title="Confirm Completed Work?"
        message="The worker has marked this job as done. Confirm that the work is complete so you can proceed to payment."
        confirmLabel="Yes, Confirm Completion"
        cancelLabel="Not Yet"
        onConfirm={handleConfirmCompletion}
        onCancel={() => setConfirmTargetId(null)}
      />

      <ConfirmDialog
        visible={payTargetId !== null}
        title="Complete Demo Payment?"
        message="This is a demo payment for this project — no real money or payment provider is involved. Confirm to mark this request as paid."
        confirmLabel="Yes, Pay Now (Demo)"
        cancelLabel="Not Yet"
        onConfirm={handleConfirmPayment}
        onCancel={() => setPayTargetId(null)}
      />
    </View>
  );
}

interface RequestCardProps {
  request: LocalServiceRequest;
  isActioning: boolean;
  onCancel: () => void;
  onConfirmCompletion: () => void;
  onPay: () => void;
}

/**
 * Resolves a status "tone" to its badge/text style pair. A plain
 * function (rather than a module-level lookup object built from
 * `styles.*`) because `styles = StyleSheet.create(...)` below is
 * declared after this component in the file — evaluating `styles.*` at
 * module-load time here would hit the `const` temporal-dead-zone. Called
 * only at render time, well after the whole module has finished
 * evaluating, so `styles` is safely defined by then.
 */
function getStatusBadgeStyle(tone: StatusTone): { badge: object; text: object } {
  switch (tone) {
    case 'active':
      return { badge: styles.statusBadgeActive, text: styles.statusBadgeTextActive };
    case 'attention':
      return { badge: styles.statusBadgeAttention, text: styles.statusBadgeTextAttention };
    case 'success':
      return { badge: styles.statusBadgeSuccess, text: styles.statusBadgeTextSuccess };
    case 'cancelled':
      return { badge: styles.statusBadgeCancelled, text: styles.statusBadgeTextCancelled };
  }
}

function RequestCard({ request, isActioning, onCancel, onConfirmCompletion, onPay }: RequestCardProps) {
  const isCancelled = request.status === 'CANCELLED_BY_USER';
  const isActive = CANCELLABLE_STATUSES.includes(request.status);
  const showConfirm = request.status === 'WORKER_COMPLETED';
  const showPay = request.status === 'PAYMENT_PENDING';
  const { label: statusLabel, tone: statusTone } = STATUS_DISPLAY[request.status];
  const badgeStyle = getStatusBadgeStyle(statusTone);

  return (
    <View style={[styles.card, isCancelled && styles.cardCancelled]}>
      <View style={styles.cardHeaderRow}>
        <Text style={styles.cardService}>{request.serviceName}</Text>
        <View style={[styles.statusBadge, badgeStyle.badge]}>
          <Text style={[styles.statusBadgeText, badgeStyle.text]}>{statusLabel}</Text>
        </View>
      </View>

      <View style={styles.cardDetailRow}>
        <Ionicons name="calendar-outline" size={14} color={colors.textSecondary} />
        <Text style={styles.cardDetailText}>{request.dateTimeLabel}</Text>
      </View>
      <View style={styles.cardDetailRow}>
        <Ionicons name="business-outline" size={14} color={colors.textSecondary} />
        <Text style={styles.cardDetailText}>{request.associationName}</Text>
      </View>
      <View style={styles.cardDetailRow}>
        <Ionicons name="location-outline" size={14} color={colors.textSecondary} />
        <Text style={styles.cardDetailText} numberOfLines={2}>
          {request.address}
        </Text>
      </View>

      {/*
       * Phase 6E-B: only rendered once the backend actually provides it
       * (`assignedWorkerName` populates once the request's current
       * Assignment reaches ACCEPTED/COMPLETED — see
       * `ServiceRequestPublic`'s docstring). Never fabricated or guessed
       * client-side; absent entirely otherwise.
       */}
      {request.assignedWorkerName ? (
        <View style={styles.cardDetailRow}>
          <Ionicons name="person-outline" size={14} color={colors.textSecondary} />
          <Text style={styles.cardDetailText}>
            Worker: {request.assignedWorkerName}
            {request.assignedWorkerPhone ? ` · ${request.assignedWorkerPhone}` : ''}
          </Text>
        </View>
      ) : null}

      {isActive ? (
        <Pressable
          style={[styles.cancelButton, isActioning && styles.cancelButtonDisabled]}
          onPress={onCancel}
          disabled={isActioning}
        >
          {isActioning ? (
            <ActivityIndicator color={colors.error} size="small" />
          ) : (
            <Text style={styles.cancelButtonText}>Cancel Request</Text>
          )}
        </Pressable>
      ) : null}

      {showConfirm ? (
        <Pressable
          style={[styles.confirmButton, isActioning && styles.cancelButtonDisabled]}
          onPress={onConfirmCompletion}
          disabled={isActioning}
        >
          {isActioning ? (
            <ActivityIndicator color={colors.white} size="small" />
          ) : (
            <Text style={styles.confirmButtonText}>Confirm Completion</Text>
          )}
        </Pressable>
      ) : null}

      {showPay ? (
        <Pressable
          style={[styles.payButton, isActioning && styles.cancelButtonDisabled]}
          onPress={onPay}
          disabled={isActioning}
        >
          {isActioning ? (
            <ActivityIndicator color={colors.white} size="small" />
          ) : (
            <Text style={styles.payButtonText}>Pay Now (Demo)</Text>
          )}
        </Pressable>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: colors.white,
  },
  headerWrap: {
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.xl,
    paddingBottom: spacing.sm,
  },
  content: {
    paddingHorizontal: spacing.lg,
    paddingBottom: spacing.lg,
  },
  title: {
    ...typography.heading,
    fontSize: 22,
  },
  subtitle: {
    ...typography.subheading,
    marginTop: 4,
    marginBottom: spacing.lg,
  },
  emptyState: {
    alignItems: 'center',
    paddingVertical: spacing.xl,
    gap: spacing.xs,
  },
  emptyTitle: {
    fontSize: 15,
    fontWeight: '800',
    color: colors.navy,
  },
  emptyBody: {
    fontSize: 12,
    color: colors.textSecondary,
    marginBottom: spacing.md,
  },
  emptyAction: {
    borderWidth: 1,
    borderColor: colors.blue,
    borderRadius: radius.pill,
    paddingVertical: 10,
    paddingHorizontal: spacing.lg,
  },
  emptyActionText: {
    color: colors.blue,
    fontWeight: '700',
    fontSize: 13,
  },
  centerState: {
    alignItems: 'center',
    paddingVertical: spacing.xl,
    gap: spacing.sm,
  },
  centerStateText: {
    fontSize: 13,
    color: colors.textSecondary,
  },
  retryButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    borderWidth: 1,
    borderColor: colors.blue,
    borderRadius: radius.pill,
    paddingVertical: 10,
    paddingHorizontal: spacing.lg,
  },
  retryButtonText: {
    color: colors.blue,
    fontWeight: '700',
    fontSize: 13,
  },
  errorCard: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: spacing.sm,
    backgroundColor: '#FCEBEB',
    borderWidth: 1,
    borderColor: colors.error,
    borderRadius: radius.md,
    padding: spacing.md,
    marginBottom: spacing.lg,
  },
  errorCardText: {
    flex: 1,
    fontSize: 12,
    color: colors.error,
    lineHeight: 17,
    fontWeight: '600',
  },
  card: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    padding: spacing.md,
    marginBottom: spacing.md,
  },
  cardCancelled: {
    opacity: 0.6,
  },
  cardHeaderRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    gap: spacing.sm,
    marginBottom: spacing.sm,
  },
  cardService: {
    flex: 1,
    fontSize: 15,
    fontWeight: '800',
    color: colors.navy,
  },
  statusBadge: {
    borderRadius: radius.pill,
    paddingHorizontal: spacing.sm,
    paddingVertical: 3,
  },
  statusBadgeActive: {
    backgroundColor: colors.blueTint,
  },
  statusBadgeAttention: {
    backgroundColor: '#FEF3E2',
  },
  statusBadgeSuccess: {
    backgroundColor: colors.greenTint,
  },
  statusBadgeCancelled: {
    backgroundColor: colors.background,
  },
  statusBadgeText: {
    fontSize: 11,
    fontWeight: '700',
  },
  statusBadgeTextActive: {
    color: colors.blue,
  },
  statusBadgeTextAttention: {
    color: colors.warning,
  },
  statusBadgeTextSuccess: {
    color: colors.success,
  },
  statusBadgeTextCancelled: {
    color: colors.textMuted,
  },
  cardDetailRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: spacing.xs,
    marginBottom: 4,
  },
  cardDetailText: {
    flex: 1,
    fontSize: 12,
    color: colors.textSecondary,
  },
  cancelButton: {
    borderWidth: 1,
    borderColor: colors.error,
    borderRadius: radius.pill,
    paddingVertical: 10,
    alignItems: 'center',
    marginTop: spacing.sm,
  },
  cancelButtonDisabled: {
    opacity: 0.6,
  },
  cancelButtonText: {
    color: colors.error,
    fontWeight: '700',
    fontSize: 13,
  },
  confirmButton: {
    backgroundColor: colors.blue,
    borderRadius: radius.pill,
    paddingVertical: 10,
    alignItems: 'center',
    marginTop: spacing.sm,
  },
  confirmButtonText: {
    color: colors.white,
    fontWeight: '700',
    fontSize: 13,
  },
  payButton: {
    backgroundColor: colors.green,
    borderRadius: radius.pill,
    paddingVertical: 10,
    alignItems: 'center',
    marginTop: spacing.sm,
  },
  payButtonText: {
    color: colors.white,
    fontWeight: '700',
    fontSize: 13,
  },
});
