import { Ionicons } from '@expo/vector-icons';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { ScreenHeader } from '../../components/ScreenHeader';
import { useAuth } from '../../features/auth';
import { DEMO_ADDRESS, useRequests } from '../../features/requests';
import { colors, radius, spacing, typography } from '../../constants/theme';

/**
 * Phase 3D — the last review step before a request is sent. Only
 * displays/forwards what Phase 3A/3B/3C already selected; it never
 * re-derives or invents any of that data.
 */
export default function ConfirmRequestScreen() {
  const router = useRouter();
  const { session, logout } = useAuth();
  const { submitRequest } = useRequests();
  const { serviceId, serviceName, dateTimeLabel, associationId, associationName } = useLocalSearchParams<{
    serviceId?: string;
    serviceName?: string;
    dateTimeLabel?: string;
    associationId?: string;
    associationName?: string;
  }>();

  const hasRequiredParams = Boolean(serviceId && serviceName && dateTimeLabel && associationId && associationName);

  const handleLogout = () => {
    logout();
    router.replace('/role-selection');
  };

  const handleSendRequest = () => {
    if (!hasRequiredParams) return;
    const request = submitRequest({
      serviceId: serviceId as string,
      serviceName: serviceName as string,
      dateTimeLabel: dateTimeLabel as string,
      associationId: associationId as string,
      associationName: associationName as string,
    });
    router.replace({
      pathname: '/(user)/request-submitted',
      params: { requestId: request.requestId },
    });
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
        <Text style={styles.title}>Confirm Request</Text>
        <Text style={styles.subtitle}>Review your service request before sending it.</Text>

        {hasRequiredParams ? (
          <View style={styles.summaryCard}>
            <View style={styles.summaryRow}>
              <Text style={styles.summaryLabel}>Service</Text>
              <Text style={styles.summaryValue}>{serviceName}</Text>
            </View>
            <View style={styles.summaryDivider} />
            <View style={styles.summaryRow}>
              <Text style={styles.summaryLabel}>Date &amp; Time</Text>
              <Text style={styles.summaryValue}>{dateTimeLabel}</Text>
            </View>
            <View style={styles.summaryDivider} />
            <View style={styles.summaryRow}>
              <Text style={styles.summaryLabel}>Labour Association</Text>
              <Text style={styles.summaryValue}>{associationName}</Text>
            </View>
            <View style={styles.summaryDivider} />
            <View style={styles.summaryRow}>
              <View style={styles.addressLabelRow}>
                <Text style={styles.summaryLabel}>Service Location</Text>
                <View style={styles.demoBadge}>
                  <Text style={styles.demoBadgeText}>Demo Address</Text>
                </View>
              </View>
              <Text style={styles.summaryValue}>{DEMO_ADDRESS}</Text>
            </View>
          </View>
        ) : (
          <View style={styles.warningCard}>
            <Ionicons name="alert-circle-outline" size={18} color={colors.warning} />
            <Text style={styles.warningText}>
              Missing request details. Please go back and choose a service, schedule, and association first.
            </Text>
          </View>
        )}
      </ScrollView>

      <View style={styles.footer}>
        <Pressable style={styles.editButton} onPress={() => router.back()}>
          <Text style={styles.editButtonText}>Back / Edit</Text>
        </Pressable>
        <Pressable
          style={[styles.sendButton, !hasRequiredParams && styles.sendButtonDisabled]}
          onPress={handleSendRequest}
          disabled={!hasRequiredParams}
        >
          <Text style={styles.sendButtonText}>Send Request</Text>
        </Pressable>
      </View>
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
  summaryCard: {
    backgroundColor: colors.blueTint,
    borderRadius: radius.md,
    padding: spacing.md,
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
  addressLabelRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 2,
  },
  demoBadge: {
    backgroundColor: colors.warning,
    borderRadius: radius.pill,
    paddingHorizontal: spacing.sm,
    paddingVertical: 2,
  },
  demoBadgeText: {
    fontSize: 10,
    fontWeight: '800',
    color: colors.white,
  },
  warningCard: {
    flexDirection: 'row',
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
  },
  footer: {
    flexDirection: 'row',
    gap: spacing.md,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    borderTopWidth: 1,
    borderTopColor: colors.border,
  },
  editButton: {
    flex: 1,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.pill,
    paddingVertical: 14,
    alignItems: 'center',
  },
  editButtonText: {
    color: colors.navy,
    fontWeight: '700',
  },
  sendButton: {
    flex: 1,
    backgroundColor: colors.blue,
    borderRadius: radius.pill,
    paddingVertical: 14,
    alignItems: 'center',
  },
  sendButtonDisabled: {
    backgroundColor: colors.border,
  },
  sendButtonText: {
    color: colors.white,
    fontWeight: '700',
  },
});
