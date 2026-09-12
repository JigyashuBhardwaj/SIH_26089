import { Ionicons } from '@expo/vector-icons';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { ScreenHeader } from '../../components/ScreenHeader';
import { useAuth } from '../../features/auth';
import { useRequests } from '../../features/requests';
import { colors, radius, spacing, typography } from '../../constants/theme';

/**
 * Shown once, right after Confirm Request's "Send Request" succeeds.
 * Looks the just-created request up from the local store by id rather
 * than re-receiving all its fields as params — this is also exactly the
 * shape a real "fetch by id" would have once a backend exists.
 */
export default function RequestSubmittedScreen() {
  const router = useRouter();
  const { session, logout } = useAuth();
  const { getRequest } = useRequests();
  const { requestId } = useLocalSearchParams<{ requestId?: string }>();

  const request = requestId ? getRequest(requestId) : undefined;

  const handleLogout = () => {
    logout();
    router.replace('/role-selection');
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
        {request ? (
          <>
            <View style={styles.successIconWrap}>
              <Ionicons name="checkmark-circle" size={56} color={colors.success} />
            </View>
            <Text style={styles.title}>Request Submitted</Text>
            <Text style={styles.subtitle}>
              Your service request has been sent to the selected labour association.
            </Text>

            <View style={styles.summaryCard}>
              <View style={styles.summaryRow}>
                <Text style={styles.summaryLabel}>Service</Text>
                <Text style={styles.summaryValue}>{request.serviceName}</Text>
              </View>
              <View style={styles.summaryDivider} />
              <View style={styles.summaryRow}>
                <Text style={styles.summaryLabel}>Date &amp; Time</Text>
                <Text style={styles.summaryValue}>{request.dateTimeLabel}</Text>
              </View>
              <View style={styles.summaryDivider} />
              <View style={styles.summaryRow}>
                <Text style={styles.summaryLabel}>Association</Text>
                <Text style={styles.summaryValue}>{request.associationName}</Text>
              </View>
            </View>

            <View style={styles.statusCard}>
              <Ionicons name="search-outline" size={20} color={colors.blue} />
              <View style={styles.statusTextWrap}>
                <Text style={styles.statusTitle}>Finding a Worker</Text>
                <Text style={styles.statusBody}>
                  The association will arrange a suitable worker for your request.
                </Text>
              </View>
            </View>

            <Pressable
              style={styles.primaryButton}
              onPress={() => router.replace('/(user)/ongoing-requests')}
            >
              <Text style={styles.primaryButtonText}>View Ongoing Request</Text>
            </Pressable>
          </>
        ) : (
          <View style={styles.warningCard}>
            <Ionicons name="alert-circle-outline" size={18} color={colors.warning} />
            <Text style={styles.warningText}>
              We couldn&apos;t find that request. It may have already been submitted — check Ongoing Requests.
            </Text>
            <Pressable
              style={styles.primaryButton}
              onPress={() => router.replace('/(user)/ongoing-requests')}
            >
              <Text style={styles.primaryButtonText}>Go to Ongoing Requests</Text>
            </Pressable>
          </View>
        )}
      </ScrollView>
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
    paddingBottom: spacing.xl,
    alignItems: 'stretch',
  },
  successIconWrap: {
    alignItems: 'center',
    marginTop: spacing.md,
    marginBottom: spacing.md,
  },
  title: {
    ...typography.heading,
    fontSize: 22,
    textAlign: 'center',
  },
  subtitle: {
    ...typography.subheading,
    textAlign: 'center',
    marginTop: 4,
    marginBottom: spacing.lg,
  },
  summaryCard: {
    backgroundColor: colors.blueTint,
    borderRadius: radius.md,
    padding: spacing.md,
    marginBottom: spacing.md,
  },
  summaryRow: {
    paddingVertical: spacing.xs,
  },
  summaryDivider: {
    height: 1,
    backgroundColor: colors.blueBorder,
    marginVertical: spacing.sm,
  },
  summaryLabel: {
    fontSize: 12,
    color: colors.textSecondary,
    marginBottom: 2,
  },
  summaryValue: {
    fontSize: 15,
    fontWeight: '800',
    color: colors.navy,
  },
  statusCard: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: spacing.sm,
    backgroundColor: colors.background,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    padding: spacing.md,
    marginBottom: spacing.lg,
  },
  statusTextWrap: {
    flex: 1,
  },
  statusTitle: {
    fontSize: 14,
    fontWeight: '800',
    color: colors.navy,
    marginBottom: 2,
  },
  statusBody: {
    fontSize: 12,
    color: colors.textSecondary,
    lineHeight: 17,
  },
  primaryButton: {
    backgroundColor: colors.blue,
    borderRadius: radius.pill,
    paddingVertical: 14,
    alignItems: 'center',
    marginTop: spacing.sm,
  },
  primaryButtonText: {
    color: colors.white,
    fontWeight: '700',
  },
  warningCard: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    alignItems: 'flex-start',
    gap: spacing.sm,
    backgroundColor: '#FEF6E7',
    borderWidth: 1,
    borderColor: colors.warning,
    borderRadius: radius.md,
    padding: spacing.md,
  },
  warningText: {
    flex: 1,
    fontSize: 12,
    color: colors.navy,
    lineHeight: 17,
    minWidth: '100%',
    marginBottom: spacing.sm,
  },
});
