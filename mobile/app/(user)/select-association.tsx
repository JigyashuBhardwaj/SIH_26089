import { Ionicons } from '@expo/vector-icons';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useMemo, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { BottomNavBar } from '../../components/BottomNavBar';
import { ScreenHeader } from '../../components/ScreenHeader';
import { useAuth } from '../../features/auth';
import { colors, radius, spacing, typography } from '../../constants/theme';
import { PREDEFINED_SERVICES } from '../../services/serviceCatalog';
import { ASSOCIATIONS, getEligibleAssociations, type Association } from '../../services/associationCatalog';

/**
 * Phase 3C — the user picks the labour ASSOCIATION that will fulfil the
 * request (not an individual worker; that's federation-controlled
 * allocation, out of scope here). Service and date/time come from Phase
 * 3A/3B via route params and are only ever displayed/forwarded, never
 * re-created — the Phase 3A catalogue stays the single source of truth
 * for what the selected service actually is.
 */
export default function SelectAssociationScreen() {
  const router = useRouter();
  const { session, logout } = useAuth();
  const { serviceId, serviceName, dateTimeLabel } = useLocalSearchParams<{
    serviceId?: string;
    serviceName?: string;
    dateTimeLabel?: string;
  }>();

  const [selectedAssociationId, setSelectedAssociationId] = useState<string | null>(null);

  const selectedService = useMemo(
    () => PREDEFINED_SERVICES.find((service) => service.id === serviceId) ?? null,
    [serviceId]
  );

  const hasRequiredParams = Boolean(selectedService && serviceName && dateTimeLabel);

  const eligibleAssociations = useMemo(
    () => (selectedService ? getEligibleAssociations(selectedService) : []),
    [selectedService]
  );

  const associationsById = useMemo(() => new Map(ASSOCIATIONS.map((association) => [association.id, association])), []);

  const handleLogout = () => {
    logout();
    router.replace('/role-selection');
  };

  const handleContinue = () => {
    const association = associationsById.get(selectedAssociationId ?? '');
    if (!hasRequiredParams || !association) return;
    router.push({
      pathname: '/(user)/confirm-request',
      params: {
        serviceId: serviceId as string,
        serviceName: serviceName as string,
        dateTimeLabel: dateTimeLabel as string,
        associationId: association.id,
        associationName: association.name,
      },
    });
  };

  const canContinue = hasRequiredParams && selectedAssociationId !== null;

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
        <Text style={styles.title}>Select Association</Text>
        <Text style={styles.subtitle}>Choose a labour association to fulfill your service request.</Text>

        {hasRequiredParams ? (
          <View style={styles.summaryCard}>
            <Text style={styles.summaryLabel}>Service</Text>
            <Text style={styles.summaryValue}>{serviceName}</Text>
            <View style={styles.summaryDivider} />
            <Text style={styles.summaryLabel}>Date &amp; Time</Text>
            <Text style={styles.summaryValue}>{dateTimeLabel}</Text>
          </View>
        ) : (
          <View style={styles.warningCard}>
            <Ionicons name="alert-circle-outline" size={18} color={colors.warning} />
            <Text style={styles.warningText}>
              Missing service or schedule details. Please go back and choose a service and a date/time first.
            </Text>
          </View>
        )}

        {hasRequiredParams ? (
          <>
            <Text style={styles.sectionHeading}>Available Associations</Text>

            {eligibleAssociations.length > 0 ? (
              eligibleAssociations.map((association) => (
                <AssociationCard
                  key={association.id}
                  association={association}
                  isSelected={selectedAssociationId === association.id}
                  onPress={() => setSelectedAssociationId(association.id)}
                />
              ))
            ) : (
              <View style={styles.emptyState}>
                <Ionicons name="business-outline" size={28} color={colors.textMuted} />
                <Text style={styles.emptyTitle}>No associations available</Text>
                <Text style={styles.emptyBody}>
                  No labour association currently supports this service. Please go back and choose a different
                  service.
                </Text>
              </View>
            )}
          </>
        ) : null}

        <Pressable
          style={[styles.continueButton, !canContinue && styles.continueButtonDisabled]}
          onPress={handleContinue}
          disabled={!canContinue}
        >
          <Text style={styles.continueButtonText}>Continue</Text>
        </Pressable>
      </ScrollView>

      <BottomNavBar
        active="book"
        onNavigateHome={() => router.replace('/(user)/home')}
        onNavigateRequests={() => router.push('/(user)/ongoing-requests')}
      />
    </View>
  );
}

interface AssociationCardProps {
  association: Association;
  isSelected: boolean;
  onPress: () => void;
}

function AssociationCard({ association, isSelected, onPress }: AssociationCardProps) {
  return (
    <Pressable
      style={[styles.associationCard, isSelected && styles.associationCardSelected]}
      onPress={onPress}
      accessibilityRole="button"
      accessibilityState={{ selected: isSelected }}
    >
      <View style={styles.associationHeaderRow}>
        <Text style={styles.associationName}>{association.name}</Text>
        <View style={[styles.radioOuter, isSelected && styles.radioOuterSelected]}>
          {isSelected ? <View style={styles.radioInner} /> : null}
        </View>
      </View>
      <Text style={styles.associationServices}>{association.displayServices.join(' • ')}</Text>
      <View style={styles.associationMetaRow}>
        <View style={styles.associationMetaItem}>
          <Ionicons name="star" size={14} color={colors.warning} />
          <Text style={styles.associationMetaText}>{association.rating}</Text>
        </View>
        <View style={styles.associationMetaItem}>
          <Ionicons name="people-outline" size={14} color={colors.textSecondary} />
          <Text style={styles.associationMetaText}>{association.workerCount} workers</Text>
        </View>
      </View>
    </Pressable>
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
    marginBottom: spacing.lg,
  },
  summaryLabel: {
    fontSize: 12,
    color: colors.textSecondary,
    marginBottom: 2,
  },
  summaryValue: {
    fontSize: 16,
    fontWeight: '800',
    color: colors.navy,
  },
  summaryDivider: {
    height: 1,
    backgroundColor: colors.blueBorder,
    marginVertical: spacing.sm,
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
    marginBottom: spacing.lg,
  },
  warningText: {
    flex: 1,
    fontSize: 12,
    color: colors.navy,
    lineHeight: 17,
  },
  sectionHeading: {
    fontSize: 16,
    fontWeight: '800',
    color: colors.navy,
    marginBottom: spacing.sm,
  },
  associationCard: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    padding: spacing.md,
    marginBottom: spacing.md,
  },
  associationCardSelected: {
    borderColor: colors.blue,
    backgroundColor: colors.blueTint,
  },
  associationHeaderRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    gap: spacing.sm,
  },
  associationName: {
    flex: 1,
    fontSize: 15,
    fontWeight: '800',
    color: colors.navy,
  },
  radioOuter: {
    width: 22,
    height: 22,
    borderRadius: 11,
    borderWidth: 2,
    borderColor: colors.border,
    alignItems: 'center',
    justifyContent: 'center',
  },
  radioOuterSelected: {
    borderColor: colors.blue,
  },
  radioInner: {
    width: 12,
    height: 12,
    borderRadius: 6,
    backgroundColor: colors.blue,
  },
  associationServices: {
    fontSize: 12,
    color: colors.textSecondary,
    marginTop: spacing.xs,
  },
  associationMetaRow: {
    flexDirection: 'row',
    gap: spacing.lg,
    marginTop: spacing.sm,
  },
  associationMetaItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  associationMetaText: {
    fontSize: 12,
    fontWeight: '700',
    color: colors.navy,
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
    paddingHorizontal: spacing.lg,
  },
  continueButton: {
    backgroundColor: colors.blue,
    paddingVertical: 14,
    borderRadius: radius.pill,
    alignItems: 'center',
    marginTop: spacing.sm,
  },
  continueButtonDisabled: {
    backgroundColor: colors.border,
  },
  continueButtonText: {
    color: colors.white,
    fontWeight: '700',
    fontSize: 16,
  },
});
