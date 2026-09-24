import { Ionicons } from '@expo/vector-icons';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { ScreenHeader } from '../../components/ScreenHeader';
import { useAuth } from '../../features/auth';
import { DEMO_ADDRESS, useRequests } from '../../features/requests';
import { ApiError, NetworkUnavailableError } from '../../services/apiClient';
import { colors, radius, spacing, typography } from '../../constants/theme';

/**
 * Turns whatever `submitRequest` rejected with into a safe, user-facing
 * message — reusing `apiClient`'s existing error types rather than
 * introducing a second HTTP/error abstraction. `ApiError`/
 * `NetworkUnavailableError` messages are already safe/user-facing (see
 * `apiClient.ts`'s `extractErrorMessage`); anything else is an
 * unexpected error, so a generic fallback is shown instead of a raw
 * stack trace.
 */
function describeSubmitError(err: unknown): string {
  if (err instanceof ApiError || err instanceof NetworkUnavailableError) {
    return err.message;
  }
  return 'Something went wrong while sending your request. Please try again.';
}

/**
 * Phase 3D — the last review step before a request is sent. Only
 * displays/forwards what Phase 3A/3B/3C already selected; it never
 * re-derives or invents any of that data.
 *
 * Phase 6B-4: "Send Request" now calls the real, authenticated
 * `submitRequest` (backed by `POST /requests`) instead of a local mock.
 * This screen never fabricates a request id/status itself — it only
 * navigates once the backend has actually created the request.
 */
export default function ConfirmRequestScreen() {
  const router = useRouter();
  const { session, logout } = useAuth();
  const { submitRequest } = useRequests();
  const { serviceId, serviceName, dateTimeLabel, requestedDateTime, associationId, associationName } = useLocalSearchParams<{
    serviceId?: string;
    serviceName?: string;
    dateTimeLabel?: string;
    requestedDateTime?: string;
    associationId?: string;
    associationName?: string;
  }>();

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const hasRequiredParams = Boolean(
    serviceId && serviceName && dateTimeLabel && requestedDateTime && associationId && associationName
  );

  const handleLogout = () => {
    logout();
    router.replace('/role-selection');
  };

  const handleSendRequest = async () => {
    // Guards against both missing params and a second tap while the
    // first submission is still in flight — no duplicate POST from
    // double taps.
    if (!hasRequiredParams || isSubmitting) return;

    setIsSubmitting(true);
    setSubmitError(null);

    try {
      const request = await submitRequest({
        serviceId: serviceId as string,
        serviceName: serviceName as string,
        requestedDateTime: requestedDateTime as string,
        dateTimeLabel: dateTimeLabel as string,
        associationId: associationId as string,
        associationName: associationName as string,
      });
      // Real backend id only — never requestCode, never a fabricated value.
      router.replace({
        pathname: '/(user)/request-submitted',
        params: { requestId: request.requestId },
      });
    } catch (err) {
      // Stay on this screen, surface a safe message, and allow retry —
      // no local fake request is ever created on failure.
      setSubmitError(describeSubmitError(err));
      setIsSubmitting(false);
    }
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

        {submitError ? (
          <View style={styles.errorCard}>
            <Ionicons name="close-circle-outline" size={18} color={colors.error} />
            <Text style={styles.errorText}>{submitError}</Text>
          </View>
        ) : null}
      </ScrollView>

      <View style={styles.footer}>
        <Pressable style={styles.editButton} onPress={() => router.back()} disabled={isSubmitting}>
          <Text style={styles.editButtonText}>Back / Edit</Text>
        </Pressable>
        <Pressable
          style={[styles.sendButton, (!hasRequiredParams || isSubmitting) && styles.sendButtonDisabled]}
          onPress={handleSendRequest}
          disabled={!hasRequiredParams || isSubmitting}
        >
          {isSubmitting ? (
            <ActivityIndicator color={colors.white} />
          ) : (
            <Text style={styles.sendButtonText}>Send Request</Text>
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
  errorCard: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: spacing.sm,
    backgroundColor: '#FCEBEB',
    borderWidth: 1,
    borderColor: colors.error,
    borderRadius: radius.md,
    padding: spacing.md,
    marginTop: spacing.md,
  },
  errorText: {
    flex: 1,
    fontSize: 12,
    color: colors.error,
    lineHeight: 17,
    fontWeight: '600',
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
