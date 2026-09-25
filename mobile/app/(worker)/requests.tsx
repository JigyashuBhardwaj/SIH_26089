import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { ActivityIndicator, Pressable, RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';
import { ConfirmDialog } from '../../components/ConfirmDialog';
import type { Assignment } from '@shared/types';
import { ApiError } from '../../services/apiClient';
import {
  acceptAssignment,
  declineAssignment,
  describeAcceptError,
  describeDeclineError,
  describeFetchAssignmentsError,
  fetchOwnAssignments,
} from '../../services/workerAssignments';
import { colors, radius, spacing, typography } from '../../constants/theme';

type LoadState = 'idle' | 'loading' | 'error' | 'ready';

/**
 * Formats an assignment's `assignedAt` ISO timestamp for display. Kept as
 * a small local duplicate rather than importing a shared helper — same
 * convention `RequestsContext.tsx`'s `formatRequestedDateTimeLabel`
 * already established for exactly this situation (deriving a display
 * label from a backend-returned ISO string).
 */
function formatAssignedAtLabel(isoDateTime: string): string {
  const date = new Date(isoDateTime);
  const dateLabel = date.toLocaleDateString(undefined, { day: 'numeric', month: 'long', year: 'numeric' });
  const timeLabel = date.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit', hour12: true });
  return `${dateLabel}, ${timeLabel}`;
}

/**
 * A short, human-scannable reference derived from the assignment's
 * `requestId` — NOT the same as the backend's own `REQ-xxxxx` request
 * code. Used ONLY as a fallback when `assignment.requestSummary` is
 * unavailable for some reason (e.g. an older cached value) — the normal
 * case now uses the real `requestSummary.requestCode`/`serviceName`/etc,
 * joined server-side as of Phase 6E-A (`GET /workers/me/assignments`).
 */
function shortRequestRef(requestId: string): string {
  return requestId.slice(0, 8).toUpperCase();
}

/**
 * Reachable from Worker Home "Booking Requests" card. Phase 6D: lists the
 * authenticated worker's own real, currently-pending Assignment offers
 * (`GET /workers/me/assignments`, filtered to `PENDING_RESPONSE` — the
 * backend has no "pending only" filter of its own) and lets the worker
 * Accept (`POST /assignments/{id}/accept`) or Decline
 * (`POST /assignments/{id}/decline`) each one. Backend/PostgreSQL is the
 * single source of truth throughout: nothing here is fabricated or
 * inferred client-side, and every mutation updates local state only from
 * the backend's own response.
 */
export default function BookingRequestsScreen() {
  const router = useRouter();

  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [loadState, setLoadState] = useState<LoadState>('idle');
  const [loadError, setLoadError] = useState<string | null>(null);

  // The one assignment currently being accepted/declined (if any) —
  // disables that specific card's buttons so the same in-flight action
  // can't be submitted twice. Mirrors `cancellingId` in
  // `ongoing-requests.tsx`.
  const [actioningId, setActioningId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [declineTargetId, setDeclineTargetId] = useState<string | null>(null);

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

  // Booking Requests = offers still awaiting the worker's response. The
  // backend's own history endpoint returns every assignment ever made to
  // this worker (no "active only" filter) — this screen narrows that
  // down client-side, the same way `ongoing-requests.tsx` filters
  // `RequestsContext`'s full list rather than the backend doing it.
  const pendingAssignments = useMemo(
    () => assignments.filter((assignment) => assignment.status === 'PENDING_RESPONSE'),
    [assignments]
  );

  const applyUpdatedAssignment = (updated: Assignment) => {
    setAssignments((previous) => previous.map((assignment) => (assignment.id === updated.id ? updated : assignment)));
  };

  const handleAccept = async (assignmentId: string) => {
    if (actioningId) return;
    setActioningId(assignmentId);
    setActionError(null);
    try {
      const updated = await acceptAssignment(assignmentId);
      applyUpdatedAssignment(updated);
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        // Our local view of this assignment is stale (already
        // responded to, or the request moved on) — reconcile with the
        // backend instead of fabricating a status.
        await loadAssignments();
      } else {
        setActionError(describeAcceptError(err));
      }
    } finally {
      setActioningId(null);
    }
  };

  const handleConfirmDecline = async () => {
    if (!declineTargetId || actioningId) return;
    const targetId = declineTargetId;
    setDeclineTargetId(null);
    setActioningId(targetId);
    setActionError(null);
    try {
      const updated = await declineAssignment(targetId);
      applyUpdatedAssignment(updated);
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        await loadAssignments();
      } else {
        setActionError(describeDeclineError(err));
      }
    } finally {
      setActioningId(null);
    }
  };

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
        <Text style={styles.title}>Booking Requests</Text>
        <Text style={styles.subtitle}>Offers waiting for your response.</Text>

        {actionError ? (
          <View style={styles.errorCard}>
            <Ionicons name="close-circle-outline" size={18} color={colors.error} />
            <Text style={styles.errorCardText}>{actionError}</Text>
          </View>
        ) : null}

        {isInitialLoading ? (
          <View style={styles.centerState}>
            <ActivityIndicator color={colors.green} />
            <Text style={styles.centerStateText}>Loading booking requests…</Text>
          </View>
        ) : loadState === 'error' ? (
          <View style={styles.centerState}>
            <Ionicons name="cloud-offline-outline" size={28} color={colors.textMuted} />
            <Text style={styles.emptyTitle}>Couldn&apos;t load booking requests</Text>
            <Text style={styles.emptyBody}>{loadError}</Text>
            <Pressable style={styles.retryButton} onPress={loadAssignments}>
              <Text style={styles.retryButtonText}>Retry</Text>
            </Pressable>
          </View>
        ) : pendingAssignments.length === 0 ? (
          <View style={styles.emptyState}>
            <Ionicons name="briefcase-outline" size={32} color={colors.textMuted} />
            <Text style={styles.emptyTitle}>No booking requests right now</Text>
            <Text style={styles.emptyBody}>New offers from associations will show up here.</Text>
          </View>
        ) : (
          pendingAssignments.map((assignment) => (
            <AssignmentCard
              key={assignment.id}
              assignment={assignment}
              isActioning={actioningId === assignment.id}
              onAccept={() => handleAccept(assignment.id)}
              onDecline={() => setDeclineTargetId(assignment.id)}
            />
          ))
        )}
      </ScrollView>

      <ConfirmDialog
        visible={declineTargetId !== null}
        title="Decline Request?"
        message="Are you sure you want to decline this booking request?"
        confirmLabel="Yes, Decline"
        cancelLabel="Keep Request"
        destructive
        onConfirm={handleConfirmDecline}
        onCancel={() => setDeclineTargetId(null)}
      />
    </View>
  );
}

interface AssignmentCardProps {
  assignment: Assignment;
  isActioning: boolean;
  onAccept: () => void;
  onDecline: () => void;
}

function AssignmentCard({ assignment, isActioning, onAccept, onDecline }: AssignmentCardProps) {
  const summary = assignment.requestSummary;

  return (
    <View style={styles.card}>
      <View style={styles.cardHeaderRow}>
        <Text style={styles.cardRef}>
          {summary ? summary.serviceName : `Ref: ${shortRequestRef(assignment.requestId)}`}
        </Text>
        <View style={styles.statusBadge}>
          <Text style={styles.statusBadgeText}>Awaiting your response</Text>
        </View>
      </View>

      {summary ? <Text style={styles.cardSubRef}>Ref: {summary.requestCode}</Text> : null}

      <View style={styles.cardDetailRow}>
        <Ionicons name="calendar-outline" size={14} color={colors.textSecondary} />
        <Text style={styles.cardDetailText}>
          {summary ? formatAssignedAtLabel(summary.requestedDateTime) : `Offered ${formatAssignedAtLabel(assignment.assignedAt)}`}
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

      <View style={styles.actionRow}>
        <Pressable
          style={[styles.declineButton, isActioning && styles.buttonDisabled]}
          onPress={onDecline}
          disabled={isActioning}
        >
          <Text style={styles.declineButtonText}>Decline</Text>
        </Pressable>
        <Pressable
          style={[styles.acceptButton, isActioning && styles.buttonDisabled]}
          onPress={onAccept}
          disabled={isActioning}
        >
          {isActioning ? (
            <ActivityIndicator color={colors.white} size="small" />
          ) : (
            <Text style={styles.acceptButtonText}>Accept</Text>
          )}
        </Pressable>
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
  cardSubRef: {
    fontSize: 11,
    color: colors.textMuted,
    marginBottom: spacing.sm,
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
  actionRow: {
    flexDirection: 'row',
    gap: spacing.sm,
    marginTop: spacing.sm,
  },
  declineButton: {
    flex: 1,
    borderWidth: 1,
    borderColor: colors.error,
    borderRadius: radius.pill,
    paddingVertical: 10,
    alignItems: 'center',
  },
  declineButtonText: {
    color: colors.error,
    fontWeight: '700',
    fontSize: 13,
  },
  acceptButton: {
    flex: 1,
    backgroundColor: colors.green,
    borderRadius: radius.pill,
    paddingVertical: 10,
    alignItems: 'center',
  },
  acceptButtonText: {
    color: colors.white,
    fontWeight: '700',
    fontSize: 13,
  },
  buttonDisabled: {
    opacity: 0.6,
  },
});
