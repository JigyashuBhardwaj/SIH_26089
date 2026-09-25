import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { ActivityIndicator, Pressable, RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';
import { ConfirmDialog } from '../../components/ConfirmDialog';
import type { Assignment } from '@shared/types';
import { ApiError } from '../../services/apiClient';
import {
  cancelAssignment,
  completeAssignment,
  describeCancelError,
  describeCompleteError,
  describeFetchAssignmentsError,
  fetchOwnAssignments,
} from '../../services/workerAssignments';
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
 * `requestId` — NOT the backend's own `REQ-xxxxx` request code. Used ONLY
 * as a fallback when `assignment.requestSummary` is unavailable for some
 * reason (e.g. an older cached value) — the normal case now uses the real
 * `requestSummary.requestCode`/`serviceName`/etc, joined server-side as
 * of Phase 6E-A (`GET /workers/me/assignments`).
 */
function shortRequestRef(requestId: string): string {
  return requestId.slice(0, 8).toUpperCase();
}

/**
 * Reachable from Worker Home "Accepted Requests" card. Lists the
 * authenticated worker's own real Assignments currently in ACCEPTED
 * status, from the same `GET /workers/me/assignments` data `requests.tsx`
 * already fetches via `fetchOwnAssignments()` — no second API/service
 * layer.
 *
 * Phase 6E-A extends the earlier read-only version: a worker can now
 * Cancel an accepted job (`POST /assignments/{id}/cancel` — the
 * ServiceRequest returns to MATCHING for the association to reassign) or
 * mark it done (`POST /assignments/{id}/complete` — the ServiceRequest
 * moves to WORKER_COMPLETED for the User to confirm/pay, handled
 * entirely by a later phase). Both mutations follow the exact same
 * backend-authoritative, 409-reconciles-via-refetch pattern already
 * established for Accept/Decline in `requests.tsx` — nothing here
 * fabricates a new status locally. Real job details (service, requested
 * date/time, address) now come from each assignment's `requestSummary`
 * (Phase 6E-A backend enrichment) instead of the earlier synthetic
 * `Ref:` placeholder, falling back to that placeholder gracefully if
 * `requestSummary` is ever missing on a particular row rather than
 * crashing. No Maps/QR/payment integration — still out of scope.
 */
export default function AcceptedRequestsScreen() {
  const router = useRouter();

  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [loadState, setLoadState] = useState<LoadState>('idle');
  const [loadError, setLoadError] = useState<string | null>(null);

  // The one assignment currently being cancelled/completed (if any) —
  // disables that specific card's buttons so the same in-flight action
  // can't be submitted twice. Mirrors `actioningId` in `requests.tsx`.
  const [actioningId, setActioningId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [cancelTargetId, setCancelTargetId] = useState<string | null>(null);
  const [completeTargetId, setCompleteTargetId] = useState<string | null>(null);

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
  // backend endpoint itself applies no status filter. A cancelled or
  // completed assignment naturally drops out of this list on the next
  // load/reconcile, since its status is no longer ACCEPTED — no local
  // "remove from list" logic is needed.
  const acceptedAssignments = useMemo(
    () => assignments.filter((assignment) => assignment.status === 'ACCEPTED'),
    [assignments]
  );

  const applyUpdatedAssignment = (updated: Assignment) => {
    setAssignments((previous) => previous.map((assignment) => (assignment.id === updated.id ? updated : assignment)));
  };

  const handleConfirmCancel = async () => {
    if (!cancelTargetId || actioningId) return;
    const targetId = cancelTargetId;
    setCancelTargetId(null);
    setActioningId(targetId);
    setActionError(null);
    try {
      const updated = await cancelAssignment(targetId);
      applyUpdatedAssignment(updated);
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        // Our local view of this assignment is stale — reconcile with
        // the backend instead of fabricating a status.
        await loadAssignments();
      } else {
        setActionError(describeCancelError(err));
      }
    } finally {
      setActioningId(null);
    }
  };

  const handleConfirmComplete = async () => {
    if (!completeTargetId || actioningId) return;
    const targetId = completeTargetId;
    setCompleteTargetId(null);
    setActioningId(targetId);
    setActionError(null);
    try {
      const updated = await completeAssignment(targetId);
      applyUpdatedAssignment(updated);
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        await loadAssignments();
      } else {
        setActionError(describeCompleteError(err));
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
        <Text style={styles.title}>Accepted Requests</Text>
        <Text style={styles.subtitle}>Jobs you've accepted.</Text>

        {actionError ? (
          <View style={styles.errorCard}>
            <Ionicons name="close-circle-outline" size={18} color={colors.error} />
            <Text style={styles.errorCardText}>{actionError}</Text>
          </View>
        ) : null}

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
          acceptedAssignments.map((assignment) => (
            <AcceptedAssignmentCard
              key={assignment.id}
              assignment={assignment}
              isActioning={actioningId === assignment.id}
              onCancel={() => setCancelTargetId(assignment.id)}
              onComplete={() => setCompleteTargetId(assignment.id)}
            />
          ))
        )}
      </ScrollView>

      <ConfirmDialog
        visible={cancelTargetId !== null}
        title="Cancel This Job?"
        message="You already accepted this job. Cancelling will send it back to the association for reassignment, and cannot be undone."
        confirmLabel="Yes, Cancel Job"
        cancelLabel="Keep Job"
        destructive
        onConfirm={handleConfirmCancel}
        onCancel={() => setCancelTargetId(null)}
      />

      <ConfirmDialog
        visible={completeTargetId !== null}
        title="Mark Work as Done?"
        message="Confirm that you have finished this job. The customer will be asked to confirm and complete payment next."
        confirmLabel="Yes, Mark as Done"
        cancelLabel="Not Yet"
        onConfirm={handleConfirmComplete}
        onCancel={() => setCompleteTargetId(null)}
      />
    </View>
  );
}

interface AcceptedAssignmentCardProps {
  assignment: Assignment;
  isActioning: boolean;
  onCancel: () => void;
  onComplete: () => void;
}

function AcceptedAssignmentCard({ assignment, isActioning, onCancel, onComplete }: AcceptedAssignmentCardProps) {
  const summary = assignment.requestSummary;

  return (
    <View style={styles.card}>
      <View style={styles.cardHeaderRow}>
        <Text style={styles.cardTitle}>
          {summary ? summary.serviceName : `Ref: ${shortRequestRef(assignment.requestId)}`}
        </Text>
        <View style={styles.statusBadge}>
          <Text style={styles.statusBadgeText}>Accepted</Text>
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

      {assignment.respondedAt ? (
        <View style={styles.cardDetailRow}>
          <Ionicons name="checkmark-circle-outline" size={14} color={colors.textSecondary} />
          <Text style={styles.cardDetailText}>Accepted {formatDateTimeLabel(assignment.respondedAt)}</Text>
        </View>
      ) : null}

      <View style={styles.actionRow}>
        <Pressable
          style={[styles.cancelButton, isActioning && styles.buttonDisabled]}
          onPress={onCancel}
          disabled={isActioning}
        >
          <Text style={styles.cancelButtonText}>Cancel</Text>
        </Pressable>
        <Pressable
          style={[styles.completeButton, isActioning && styles.buttonDisabled]}
          onPress={onComplete}
          disabled={isActioning}
        >
          {isActioning ? (
            <ActivityIndicator color={colors.white} size="small" />
          ) : (
            <Text style={styles.completeButtonText}>Mark Work as Done</Text>
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
  cancelButton: {
    flex: 1,
    borderWidth: 1,
    borderColor: colors.error,
    borderRadius: radius.pill,
    paddingVertical: 10,
    alignItems: 'center',
  },
  cancelButtonText: {
    color: colors.error,
    fontWeight: '700',
    fontSize: 13,
  },
  completeButton: {
    flex: 1.4,
    backgroundColor: colors.green,
    borderRadius: radius.pill,
    paddingVertical: 10,
    alignItems: 'center',
  },
  completeButtonText: {
    color: colors.white,
    fontWeight: '700',
    fontSize: 13,
  },
  buttonDisabled: {
    opacity: 0.6,
  },
});
