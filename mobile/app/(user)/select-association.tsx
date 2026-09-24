import { Ionicons } from '@expo/vector-icons';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { BottomNavBar } from '../../components/BottomNavBar';
import { ScreenHeader } from '../../components/ScreenHeader';
import { useAuth } from '../../features/auth';
import { colors, radius, spacing, typography } from '../../constants/theme';
import { describeAssociationCatalogError, fetchAssociationCatalog } from '../../services/associationCatalog';
import type { Association } from '@shared/types';

type CatalogLoadState = 'loading' | 'error' | 'ready';

/**
 * The user picks the labour ASSOCIATION that will fulfil the request
 * (not an individual worker; that's federation-controlled allocation,
 * out of scope here). Service and date/time come from the previous two
 * screens via route params and are only ever displayed/forwarded, never
 * re-created or re-resolved against any local catalogue — `serviceId`
 * arrives already carrying the real backend UUID `GET /services`
 * returned (Phase 6B-1), so this screen never fetches services itself.
 *
 * Phase 6B-2: the association list now comes from the real backend
 * (`GET /associations`, Phase 6B-pre) instead of a hardcoded local
 * catalogue. The backend has no association-service eligibility concept
 * at all, so every returned association is selectable here — no
 * category-based filtering is applied or reconstructed.
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
  const [associations, setAssociations] = useState<Association[]>([]);
  const [loadState, setLoadState] = useState<CatalogLoadState>('loading');
  const [loadError, setLoadError] = useState<string | null>(null);

  const hasRequiredParams = Boolean(serviceId && serviceName && dateTimeLabel);

  const loadAssociations = useCallback(() => {
    let cancelled = false;
    setLoadState('loading');
    setLoadError(null);

    fetchAssociationCatalog()
      .then((items) => {
        if (cancelled) return;
        setAssociations(items);
        setLoadState('ready');
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setLoadError(describeAssociationCatalogError(err));
        setLoadState('error');
      });

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => loadAssociations(), [loadAssociations]);

  const associationsById = useMemo(
    () => new Map(associations.map((association) => [association.id, association])),
    [associations]
  );

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

            {loadState === 'loading' ? (
              <View style={styles.centerState}>
                <ActivityIndicator color={colors.blue} />
                <Text style={styles.centerStateText}>Loading associations…</Text>
              </View>
            ) : loadState === 'error' ? (
              <View style={styles.centerState}>
                <Ionicons name="cloud-offline-outline" size={28} color={colors.textMuted} />
                <Text style={styles.emptyTitle}>Couldn&apos;t load associations</Text>
                <Text style={styles.emptyBody}>{loadError}</Text>
                <Pressable style={styles.retryButton} onPress={loadAssociations}>
                  <Text style={styles.retryButtonText}>Retry</Text>
                </Pressable>
              </View>
            ) : associations.length === 0 ? (
              <View style={styles.emptyState}>
                <Ionicons name="business-outline" size={28} color={colors.textMuted} />
                <Text style={styles.emptyTitle}>No associations available</Text>
                <Text style={styles.emptyBody}>There are no labour associations available right now. Please check back later.</Text>
              </View>
            ) : (
              associations.map((association) => (
                <AssociationCard
                  key={association.id}
                  association={association}
                  isSelected={selectedAssociationId === association.id}
                  onPress={() => setSelectedAssociationId(association.id)}
                />
              ))
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

/**
 * `Association` (from `@shared/types`, matching the real backend
 * `AssociationPublic`) carries only `id`/`federationId`/`name`/
 * timestamps — no rating, worker count, or service list, unlike the old
 * local mock catalogue. Rather than inventing display data the backend
 * doesn't provide, the card shows only what's real: the association's
 * name and its selection state.
 */
function AssociationCard({ association, isSelected, onPress }: AssociationCardProps) {
  return (
    <Pressable
      style={[styles.associationCard, isSelected && styles.associationCardSelected]}
      onPress={onPress}
      accessibilityRole="button"
      accessibilityState={{ selected: isSelected }}
    >
      <View style={styles.associationHeaderRow}>
        <View style={styles.associationNameRow}>
          <Ionicons name="business-outline" size={18} color={colors.blue} />
          <Text style={styles.associationName}>{association.name}</Text>
        </View>
        <View style={[styles.radioOuter, isSelected && styles.radioOuterSelected]}>
          {isSelected ? <View style={styles.radioInner} /> : null}
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
  associationNameRow: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
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
  centerState: {
    alignItems: 'center',
    paddingVertical: spacing.xl,
    gap: spacing.sm,
  },
  centerStateText: {
    fontSize: 13,
    color: colors.textSecondary,
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
