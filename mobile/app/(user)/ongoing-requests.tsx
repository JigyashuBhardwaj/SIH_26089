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
  const { requests, loadState, loadError, loadRequests, cancelRequest } = useRequests();
  const [cancelTargetId, setCancelTargetId] = useState<string | null>(null);
  // Tracks the one request currently being cancelled (if any) — disables
  // that specific card's Cancel button so the same in-flight cancellation
  // can't be submitted twice. Not shared/context state: purely this
  // screen's own transient UI concern.
  const [cancellingId, setCancellingId] = useState<string | null>(null);
  const [cancelError, setCancelError] = useState<string | null>(null);

  useEffect(() => {
    loadRequests();
  }, [loadRequests]);

  const handleLogout = () => {
    logout();
    router.replace('/role-selection');
  };

  const handleConfirmCancel = async () => {
    if (!cancelTargetId || cancellingId) return;
    const targetId = cancelTargetId;
    setCancelTargetId(null);
    setCancellingId(targetId);
    setCancelError(null);

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
        setCancelError(describeCancelError(err));
      }
    } finally {
      setCancellingId(null);
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

        {cancelError ? (
          <View style={styles.errorCard}>
            <Ionicons name="close-circle-outline" size={18} color={colors.error} />
            <Text style={styles.errorCardText}>{cancelError}</Text>
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
              isCancelling={cancellingId === request.requestId}
              onCancel={() => setCancelTargetId(request.requestId)}
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
    </View>
  );
}

interface RequestCardProps {
  request: LocalServiceRequest;
  isCancelling: boolean;
  onCancel: () => void;
}

function RequestCard({ request, isCancelling, onCancel }: RequestCardProps) {
  const isCancelled = request.status === 'CANCELLED_BY_USER';
  const isActive = CANCELLABLE_STATUSES.includes(request.status);

  return (
    <View style={[styles.card, isCancelled && styles.cardCancelled]}>
      <View style={styles.cardHeaderRow}>
        <Text style={styles.cardService}>{request.serviceName}</Text>
        <View style={[styles.statusBadge, isCancelled ? styles.statusBadgeCancelled : styles.statusBadgeActive]}>
          <Text style={[styles.statusBadgeText, isCancelled && styles.statusBadgeTextCancelled]}>
            {isCancelled ? 'Cancelled' : 'Finding a Worker'}
          </Text>
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

      {isActive ? (
        <Pressable
          style={[styles.cancelButton, isCancelling && styles.cancelButtonDisabled]}
          onPress={onCancel}
          disabled={isCancelling}
        >
          {isCancelling ? (
            <ActivityIndicator color={colors.error} size="small" />
          ) : (
            <Text style={styles.cancelButtonText}>Cancel Request</Text>
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
  statusBadgeCancelled: {
    backgroundColor: colors.background,
  },
  statusBadgeText: {
    fontSize: 11,
    fontWeight: '700',
    color: colors.blue,
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
});
