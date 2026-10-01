import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { ActivityIndicator, Pressable, RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';
import type { Assignment } from '@shared/types';
import { describeFetchAssignmentsError, fetchOwnAssignments } from '../../services/workerAssignments';
import { colors, radius, spacing, typography } from '../../constants/theme';

type LoadState = 'idle' | 'loading' | 'error' | 'ready';

/**
 * Phase 6F: the three "resolved, nothing left to do" Assignment statuses
 * shown on this screen. `requests.tsx` (Booking Requests) only ever shows
 * `PENDING_RESPONSE` and `accepted-requests.tsx` (Accepted Requests) only
 * ever shows `ACCEPTED` — both narrow the exact same
 * `fetchOwnAssignments()` result client-side, the same way this screen
 * does. These three statuses were always included in that backend
 * response (no "active only" filter server-side) but had nowhere to be
 * shown before this screen existed.
 */
const HISTORY_STATUSES: Assignment['status'][] = ['DECLINED', 'CANCELLED_BY_WORKER', 'COMPLETED'];

type StatusTone = 'declined' | 'cancelled' | 'completed';

/**
 * Distinct label + tone per history status so a worker can never mistake
 * one for another — in particular `DECLINED` (an offer the worker never
 * accepted) and `CANCELLED_BY_WORKER` (a job the worker accepted and then
 * had to back out of) are easy to conflate if not labeled and colored
 * differently. `COMPLETED` reuses the same green "success" tone the User
 * app already uses for a finished job.
 */
const STATUS_META: Record<'DECLINED' | 'CANCELLED_BY_WORKER' | 'COMPLETED', { label: string; tone: StatusTone }> = {
  DECLINED: { label: 'Declined', tone: 'declined' },
  CANCELLED_BY_WORKER: { label: 'Cancelled by You', tone: 'cancelled' },
  COMPLETED: { label: 'Completed', tone: 'completed' },
};

/**
 * Formats an ISO timestamp for display. Local duplicate of the same
 * helper already in `requests.tsx`/`accepted-requests.tsx` — same
 * file-local convention those two already established, not shared.
 */
function formatDateTimeLabel(isoDateTime: string): string {
  const date = new Date(isoDateTime);
  const dateLabel = date.toLocaleDateString(undefined, { day: 'numeric', month: 'long', year: 'numeric' });
  const timeLabel = date.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit', hour12: true });
  return `${dateLabel}, ${timeLabel}`;
}

/**
 * A short, human-scannable reference derived from the assignment's
 * `requestId` — same fallback convention as `requests.tsx`/
 * `accepted-requests.tsx`, used only when `requestSummary` is missing.
 */
function shortRequestRef(requestId: string): string {
  return requestId.slice(0, 8).toUpperCase();
}

/**
 * Reachable from Worker Home's "Booking History" card. Read-only: shows
 * every assignment that's no longer active — declined, cancelled by the
 * worker after accepting, or completed — reusing the exact same
 * `fetchOwnAssignments()` data `requests.tsx`/`accepted-requests.tsx`
 * already fetch (no new API call, no new service function). Nothing here
 * can be acted on, so there are no buttons and no ConfirmDialogs.
 */
export default function AssignmentHistoryScreen() {
  const router = useRouter();

  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [loadState, setLoadState] = useState<LoadState>('idle');
  const [loadError, setLoadError] = useState<string | null>(null);

  const loadAssignments = useCallback(async () => {
    setLoadState('loading');
    setLoadError(null);
    try {
      const all = await fetchOwnAssignments();
      setAssignments(all);
      setLoadState('ready');
    } catch (err) {
      setLoadError(describeFetchAssignmentsError(err));
      setLoadState('error');
    }
  }, []);

  useEffect(() => {
    loadAssignments();
  }, [loadAssignments]);

  const historyAssignments = useMemo(
    () => assignments.filter((assignment) => HISTORY_STATUSES.includes(assignment.status)),
    [assignments]
  );

  const isRefreshing = loadState === 'loading' && historyAssignments.length > 0;
  const isInitialLoading = loadState === 'loading' && historyAssignments.length === 0;

  return (
    <View style={styles.screen}>
      <Pressable style={styles.backButton} onPress={() => router.back()}>
        <Ionicons name="arrow-back" size={22} color={colors.navy} />
      </Pressable>

      <ScrollView
        contentContainerStyle={styles.content}
        refreshControl={<RefreshControl refreshing={isRefreshing} onRefresh={loadAssignments} />}
      >
        <Text style={styles.title}>Booking History</Text>
        <Text style={styles.subtitle}>Jobs you&apos;ve declined, cancelled, or completed.</Text>

        {isInitialLoading ? (
          <View style={styles.centerState}>
            <ActivityIndicator color={colors.green} />
            <Text style={styles.centerStateText}>Loading history…</Text>
          </View>
        ) : loadState === 'error' ? (
          <View style={styles.centerState}>
            <Ionicons name="cloud-offline-outline" size={28} color={colors.textMuted} />
            <Text style={styles.emptyTitle}>Couldn&apos;t load history</Text>
            <Text style={styles.emptyBody}>{loadError}</Text>
            <Pressable style={styles.retryButton} onPress={loadAssignments}>
              <Text style={styles.retryButtonText}>Retry</Text>
            </Pressable>
          </View>
        ) : historyAssignments.length === 0 ? (
          <View style={styles.emptyState}>
            <Ionicons name="document-text-outline" size={32} color={colors.textMuted} />
            <Text style={styles.emptyTitle}>No history yet</Text>
            <Text style={styles.emptyBody}>Declined, cancelled, and completed jobs will show up here.</Text>
          </View>
        ) : (
          historyAssignments.map((assignment) => (
            <AssignmentHistoryCard key={assignment.id} assignment={assignment} />
          ))
        )}
      </ScrollView>
    </View>
  );
}

interface AssignmentHistoryCardProps {
  assignment: Assignment;
}

/**
 * Resolves a status "tone" to its badge/text style pair — same
 * lazily-evaluated-function convention `ongoing-requests.tsx`'s
 * `getStatusBadgeStyle` already established, and for the same reason:
 * `styles` (via `StyleSheet.create`) is declared later in this file, so
 * evaluating `styles.*` at module-load time here would hit the `const`
 * temporal-dead-zone. Called only at render time, well after the module
 * has finished evaluating.
 */
function getStatusBadgeStyle(tone: StatusTone): { badge: object; text: object } {
  switch (tone) {
    case 'completed':
      return { badge: styles.statusBadgeCompleted, text: styles.statusBadgeTextCompleted };
    case 'cancelled':
      return { badge: styles.statusBadgeCancelled, text: styles.statusBadgeTextCancelled };
    case 'declined':
      return { badge: styles.statusBadgeDeclined, text: styles.statusBadgeTextDeclined };
  }
}

function AssignmentHistoryCard({ assignment }: AssignmentHistoryCardProps) {
  const summary = assignment.requestSummary;
  const { label, tone } = STATUS_META[assignment.status as 'DECLINED' | 'CANCELLED_BY_WORKER' | 'COMPLETED'];
  const badgeStyle = getStatusBadgeStyle(tone);

  return (
    <View style={styles.card}>
      <View style={styles.cardHeaderRow}>
        <Text style={styles.cardTitle}>
          {summary ? summary.serviceName : `Ref: ${shortRequestRef(assignment.requestId)}`}
        </Text>
        <View style={[styles.statusBadge, badgeStyle.badge]}>
          <Text style={[styles.statusBadgeText, badgeStyle.text]}>{label}</Text>
        </View>
      </View>

      {summary ? <Text style={styles.cardRef}>Ref: {summary.requestCode}</Text> : null}

      <View style={styles.cardDetailRow}>
        <Ionicons name="calendar-outline" size={14} color={colors.textSecondary} />
        <Text style={styles.cardDetailText}>
          {summary
            ? formatDateTimeLabel(summary.requestedDateTime)
            : `Offered ${formatDateTimeLabel(assignment.assignedAt)}`}
        </Text>
      </View>

      {summary ? (
        <View style={styles.cardDetailRow}>
          <Ionicons name="location-outline" size={14} color={colors.textSecondary} />
          <Text style={styles.cardDetailText}>
            {summary.address} — {summary.pincode}
          </Text>
        </View>
      ) : null}

      {/*
       * There's no dedicated "declinedAt"/"cancelledAt"/"completedAt"
       * field on the backend's Assignment model — only `updatedAt`
       * (auto-advanced via `onupdate=func.now()`), which is this row's
       * last-updated timestamp, not necessarily the exact moment the
       * outcome occurred. Labeled neutrally ("Updated …") rather than
       * implying more precision than the data actually carries.
       */}
      <View style={styles.cardDetailRow}>
        <Ionicons name="time-outline" size={14} color={colors.textSecondary} />
        <Text style={styles.cardDetailText}>Updated {formatDateTimeLabel(assignment.updatedAt)}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: colors.white,
    paddingTop: spacing.xl,
  },
  backButton: {
    marginBottom: spacing.md,
    paddingHorizontal: spacing.lg,
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
    borderColor: colors.green,
    borderRadius: radius.pill,
    paddingVertical: 10,
    paddingHorizontal: spacing.lg,
  },
  retryButtonText: {
    color: colors.green,
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
  cardHeaderRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    gap: spacing.sm,
    marginBottom: 4,
  },
  cardTitle: {
    flex: 1,
    fontSize: 15,
    fontWeight: '800',
    color: colors.navy,
  },
  cardRef: {
    fontSize: 11,
    color: colors.textMuted,
    marginBottom: spacing.sm,
  },
  statusBadge: {
    borderRadius: radius.pill,
    paddingHorizontal: spacing.sm,
    paddingVertical: 3,
  },
  statusBadgeCompleted: {
    backgroundColor: colors.greenTint,
  },
  statusBadgeCancelled: {
    backgroundColor: '#FCEBEB',
  },
  statusBadgeDeclined: {
    backgroundColor: colors.background,
  },
  statusBadgeText: {
    fontSize: 11,
    fontWeight: '700',
  },
  statusBadgeTextCompleted: {
    color: colors.success,
  },
  statusBadgeTextCancelled: {
    color: colors.error,
  },
  statusBadgeTextDeclined: {
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
