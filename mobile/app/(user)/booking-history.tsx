import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { useEffect, useMemo } from 'react';
import { ActivityIndicator, Pressable, RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';
import { BottomNavBar } from '../../components/BottomNavBar';
import { ScreenHeader } from '../../components/ScreenHeader';
import { useAuth } from '../../features/auth';
import { useRequests, type LocalServiceRequest } from '../../features/requests';
import { colors, radius, spacing, typography } from '../../constants/theme';

/**
 * Phase 6F: the two terminal `ServiceRequestStatus` values this screen
 * shows — the only two with an empty transition list in
 * `shared/booking/bookingStateMachine.ts` (nothing further can ever
 * happen to a request once it reaches either one). Everything else stays
 * on `mobile/app/(user)/ongoing-requests.tsx`, which now excludes these
 * two via its own `TERMINAL_STATUSES` filter.
 */
const HISTORY_STATUSES: LocalServiceRequest['status'][] = ['COMPLETED', 'CANCELLED_BY_USER'];

type StatusTone = 'success' | 'cancelled';

/** Label/tone for the two statuses this screen ever actually renders. */
const STATUS_DISPLAY: Record<'COMPLETED' | 'CANCELLED_BY_USER', { label: string; tone: StatusTone }> = {
  COMPLETED: { label: 'Completed', tone: 'success' },
  CANCELLED_BY_USER: { label: 'Cancelled', tone: 'cancelled' },
};

/**
 * Reachable from User Home's "Booking History" card (previously a
 * Coming-Soon placeholder). Read-only — reuses the exact same
 * `RequestsContext.requests` data `ongoing-requests.tsx` already loads
 * via `GET /requests` (Phase 6B-5); this screen makes no fetch of its
 * own, it only narrows the same list to the two terminal outcomes.
 * Nothing here can be cancelled, confirmed, or paid, so — unlike Ongoing
 * Requests — there are no action buttons and no ConfirmDialogs.
 */
export default function BookingHistoryScreen() {
  const router = useRouter();
  const { session, logout } = useAuth();
  const { requests, loadState, loadError, loadRequests } = useRequests();

  useEffect(() => {
    loadRequests();
  }, [loadRequests]);

  const historyRequests = useMemo(
    () => requests.filter((request) => HISTORY_STATUSES.includes(request.status)),
    [requests]
  );

  const handleLogout = () => {
    logout();
    router.replace('/role-selection');
  };

  // Same pull-to-refresh-vs-first-load split as ongoing-requests.tsx,
  // scoped to this screen's own (narrower) list.
  const isRefreshing = loadState === 'loading' && historyRequests.length > 0;
  const isInitialLoading = loadState === 'loading' && historyRequests.length === 0;

  return (
    <View style={styles.screen}>
      <View style={styles.headerWrap}>
        <ScreenHeader profileName={session?.displayName ?? 'User'} profileRoleLabel="User" onLogout={handleLogout} />
      </View>

      <ScrollView
        contentContainerStyle={styles.content}
        refreshControl={<RefreshControl refreshing={isRefreshing} onRefresh={loadRequests} />}
      >
        <Text style={styles.title}>Booking History</Text>
        <Text style={styles.subtitle}>Your completed and cancelled requests.</Text>

        {isInitialLoading ? (
          <View style={styles.centerState}>
            <ActivityIndicator color={colors.blue} />
            <Text style={styles.centerStateText}>Loading history…</Text>
          </View>
        ) : loadState === 'error' ? (
          <View style={styles.centerState}>
            <Ionicons name="cloud-offline-outline" size={28} color={colors.textMuted} />
            <Text style={styles.emptyTitle}>Couldn&apos;t load history</Text>
            <Text style={styles.emptyBody}>{loadError}</Text>
            <Pressable style={styles.retryButton} onPress={() => loadRequests()}>
              <Text style={styles.retryButtonText}>Retry</Text>
            </Pressable>
          </View>
        ) : historyRequests.length === 0 ? (
          <View style={styles.emptyState}>
            <Ionicons name="document-text-outline" size={32} color={colors.textMuted} />
            <Text style={styles.emptyTitle}>No history yet</Text>
            <Text style={styles.emptyBody}>Completed and cancelled requests will show up here.</Text>
          </View>
        ) : (
          historyRequests.map((request) => <HistoryCard key={request.requestId} request={request} />)
        )}
      </ScrollView>

      <BottomNavBar
        active="requests"
        onNavigateHome={() => router.replace('/(user)/home')}
        onNavigateRequests={() => router.push('/(user)/ongoing-requests')}
      />
    </View>
  );
}

interface HistoryCardProps {
  request: LocalServiceRequest;
}

/**
 * Reuses the same card layout/detail rows as `ongoing-requests.tsx`'s
 * `RequestCard`, minus the action buttons (nothing is actionable once a
 * request is terminal) — and the same badge tone convention (green tint
 * for a success outcome, muted grey for cancelled) rather than inventing
 * a new visual language for this screen.
 */
function HistoryCard({ request }: HistoryCardProps) {
  const { label, tone } = STATUS_DISPLAY[request.status as 'COMPLETED' | 'CANCELLED_BY_USER'];
  const isCancelled = tone === 'cancelled';

  return (
    <View style={[styles.card, isCancelled && styles.cardCancelled]}>
      <View style={styles.cardHeaderRow}>
        <Text style={styles.cardService}>{request.serviceName}</Text>
        <View style={[styles.statusBadge, isCancelled ? styles.statusBadgeCancelled : styles.statusBadgeSuccess]}>
          <Text
            style={[styles.statusBadgeText, isCancelled ? styles.statusBadgeTextCancelled : styles.statusBadgeTextSuccess]}
          >
            {label}
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

      {/*
       * Same "only render once the backend actually provides it" rule as
       * ongoing-requests.tsx's RequestCard — still relevant for a
       * COMPLETED request (the worker who did the job stays meaningful
       * history), never fabricated.
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
  centerState: {
    alignItems: 'center',
    paddingVertical: spacing.xl,
    gap: spacing.sm,
  },
  centerStateText: {
    fontSize: 13,
    color: colors.textSecondary,
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
    textAlign: 'center',
    marginBottom: spacing.md,
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
  card: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    padding: spacing.md,
    marginBottom: spacing.md,
  },
  cardCancelled: {
    opacity: 0.75,
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
});
