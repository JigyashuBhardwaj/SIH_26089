import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { ActivityIndicator, Pressable, RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';
import type { Assignment } from '@shared/types';
import { describeFetchAssignmentsError, fetchOwnAssignments } from '../../services/workerAssignments';
import { colors, radius, spacing, typography } from '../../constants/theme';

type LoadState = 'idle' | 'loading' | 'error' | 'ready';

/**
 * Formats an ISO timestamp for display. Local duplicate of the same
 * helper in `requests.tsx` — kept file-local rather than shared, the
 * same convention `RequestsContext.tsx`'s `formatRequestedDateTimeLabel`
 * already established for this exact situation.
 */
function formatDateTimeLabel(isoDateTime: string): string {
  const date = new Date(isoDateTime);
  const dateLabel = date.toLocaleDateString(undefined, { day: 'numeric', month: 'long', year: 'numeric' });
  const timeLabel = date.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit', hour12: true });
  return `${dateLabel}, ${timeLabel}`;
}

/**
 * A short, human-scannable reference derived from the assignment's
 * `requestId` — NOT the backend's own `REQ-xxxxx` request code. Same
 * helper/rationale as `requests.tsx`'s `shortRequestRef`: `AssignmentPublic`
 * (the only data a WORKER account can fetch) carries `requestId` as a
 * UUID only, with no WORKER-accessible endpoint to resolve it to the
 * real request code, service name, or address.
 */
function shortRequestRef(requestId: string): string {
  return requestId.slice(0, 8).toUpperCase();
}

/**
 * Reachable from Worker Home "Accepted Requests" card. Phase 6D
 * extension: lists the authenticated worker's own real Assignments
 * currently in ACCEPTED status, from the same `GET /workers/me/assignments`
 * data `requests.tsx` already fetches via `fetchOwnAssignments()` — no
 * second API/service layer. Read-only for now: no Cancel/Complete action,
 * no Maps/QR/payment — those are explicitly out of scope for this
 * extension.
 */
export default function AcceptedRequestsScreen() {
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

  // Accepted Requests = assignments the worker has already accepted. Same
  // full-history fetch as `requests.tsx`, narrowed client-side — the
  // backend endpoint itself applies no status filter.
  const acceptedAssignments = useMemo(
    () => assignments.filter((assignment) => assignment.status === 'ACCEPTED'),
    [assignments]
  );

  const isRefreshing = loadState === 'loading' && assignments.length > 0;
  const isInitialLoading = loadState === 'loading' && assignments.length === 0;

  return (
    <View style={styles.screen}>
      <Pressable style={styles.backButton} onPress={() => router.back()}>
        <Ionicons name="arrow-back" size={22} color={colors.navy} />
      </Pressable>

      <ScrollView
        contentContainerStyle={styles.content}
        refreshControl={<RefreshControl refreshing={isRefreshing} onRefresh={loadAssignments} />}
      >
        <Text style={styles.title}>Accepted Requests</Text>
        <Text style={styles.subtitle}>Jobs you've accepted.</Text>

        {isInitialLoading ? (
          <View style={styles.centerState}>
            <ActivityIndicator color={colors.green} />
            <Text style={styles.centerStateText}>Loading accepted requests…</Text>
          </View>
        ) : loadState === 'error' ? (
          <View style={styles.centerState}>
            <Ionicons name="cloud-offline-outline" size={28} color={colors.textMuted} />
            <Text style={styles.emptyTitle}>Couldn&apos;t load accepted requests</Text>
            <Text style={styles.emptyBody}>{loadError}</Text>
            <Pressable style={styles.retryButton} onPress={loadAssignments}>
              <Text style={styles.retryButtonText}>Retry</Text>
            </Pressable>
          </View>
        ) : acceptedAssignments.length === 0 ? (
          <View style={styles.emptyState}>
            <Ionicons name="checkmark-done-outline" size={32} color={colors.textMuted} />
            <Text style={styles.emptyTitle}>No accepted requests yet</Text>
            <Text style={styles.emptyBody}>Requests you accept from Booking Requests will show up here.</Text>
          </View>
        ) : (
          acceptedAssignments.map((assignment) => <AcceptedAssignmentCard key={assignment.id} assignment={assignment} />)
        )}
      </ScrollView>
    </View>
  );
}

function AcceptedAssignmentCard({ assignment }: { assignment: Assignment }) {
  return (
    <View style={styles.card}>
      <View style={styles.cardHeaderRow}>
        <Text style={styles.cardRef}>Ref: {shortRequestRef(assignment.requestId)}</Text>
        <View style={styles.statusBadge}>
          <Text style={styles.statusBadgeText}>Accepted</Text>
        </View>
      </View>

      {assignment.respondedAt ? (
        <View style={styles.cardDetailRow}>
          <Ionicons name="checkmark-circle-outline" size={14} color={colors.textSecondary} />
          <Text style={styles.cardDetailText}>Accepted {formatDateTimeLabel(assignment.respondedAt)}</Text>
        </View>
      ) : null}

      <View style={styles.cardDetailRow}>
        <Ionicons name="time-outline" size={14} color={colors.textSecondary} />
        <Text style={styles.cardDetailText}>Offered {formatDateTimeLabel(assignment.assignedAt)}</Text>
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
    marginBottom: spacing.sm,
  },
  cardRef: {
    flex: 1,
    fontSize: 13,
    fontWeight: '800',
    color: colors.navy,
  },
  statusBadge: {
    backgroundColor: colors.greenTint,
    borderRadius: radius.pill,
    paddingHorizontal: spacing.sm,
    paddingVertical: 3,
  },
  statusBadgeText: {
    fontSize: 11,
    fontWeight: '700',
    color: colors.green,
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
