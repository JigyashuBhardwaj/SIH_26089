import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { BottomNavBar } from '../../components/BottomNavBar';
import { ConfirmDialog } from '../../components/ConfirmDialog';
import { ScreenHeader } from '../../components/ScreenHeader';
import { useAuth } from '../../features/auth';
import { useRequests, type LocalServiceRequest } from '../../features/requests';
import { colors, radius, spacing, typography } from '../../constants/theme';

/**
 * Reachable from User Home. Lists every locally-created request (Phase
 * 3D) — both active ones ("Finding a Worker") and cancelled ones, kept
 * visible with a clear cancelled state rather than silently removed, so
 * the person still has a record of what they cancelled.
 */
export default function OngoingRequestsScreen() {
  const router = useRouter();
  const { session, logout } = useAuth();
  const { requests, cancelRequest } = useRequests();
  const [cancelTargetId, setCancelTargetId] = useState<string | null>(null);

  const handleLogout = () => {
    logout();
    router.replace('/role-selection');
  };

  const handleConfirmCancel = () => {
    if (cancelTargetId) cancelRequest(cancelTargetId);
    setCancelTargetId(null);
  };

  return (
    <View style={styles.screen}>
      <View style={styles.headerWrap}>
        <ScreenHeader
          profileName={session?.displayName ?? 'User'}
          profileRoleLabel="User"
          onLogout={handleLogout}
        />
      </View>

      <ScrollView contentContainerStyle={styles.content}>
        <Text style={styles.title}>Ongoing Requests</Text>
        <Text style={styles.subtitle}>Track and manage your service requests.</Text>

        {requests.length === 0 ? (
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
  onCancel: () => void;
}

function RequestCard({ request, onCancel }: RequestCardProps) {
  const isCancelled = request.status === 'CANCELLED_BY_USER';
  const isActive = request.status === 'MATCHING';

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
        <Pressable style={styles.cancelButton} onPress={onCancel}>
          <Text style={styles.cancelButtonText}>Cancel Request</Text>
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
  cancelButtonText: {
    color: colors.error,
    fontWeight: '700',
    fontSize: 13,
  },
});
