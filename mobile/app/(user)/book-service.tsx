import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { useMemo, useState } from 'react';
import { FlatList, Pressable, StyleSheet, Text, TextInput, View } from 'react-native';
import { BottomNavBar } from '../../components/BottomNavBar';
import { ScreenHeader } from '../../components/ScreenHeader';
import { ServiceCard } from '../../components/ServiceCard';
import { SkylineIllustration } from '../../components/illustrations/SkylineIllustration';
import { useAuth } from '../../features/auth';
import { getPopularServices, searchServices, type CatalogService } from '../../services/serviceCatalog';
import { colors, radius, spacing, typography } from '../../constants/theme';

/**
 * First screen of the User booking workflow (Phase 3A). Lets the person
 * pick a predefined service — nothing beyond that. Selecting a service
 * navigates to the Schedule Date & Time placeholder; the actual booking
 * workflow (date/time, address, association, confirmation) is built in
 * later Phase 3 steps.
 */
export default function BookServiceScreen() {
  const router = useRouter();
  const { session, logout } = useAuth();
  const [query, setQuery] = useState('');

  const isSearching = query.trim().length > 0;
  const results = useMemo(() => searchServices(query), [query]);
  const popular = useMemo(() => getPopularServices(), []);

  const handleLogout = () => {
    logout();
    router.replace('/role-selection');
  };

  const handleSelectService = (service: CatalogService) => {
    router.push({
      pathname: '/(user)/schedule',
      params: { serviceId: service.id, serviceName: service.name },
    });
  };

  return (
    <View style={styles.screen}>
      <View style={styles.headerBanner}>
        <View style={styles.headerRow}>
          <ScreenHeader
            profileName={session?.displayName ?? 'User'}
            profileRoleLabel="User"
            onLogout={handleLogout}
          />
        </View>

        <Text style={styles.title}>Book a Service</Text>
        <Text style={styles.subtitle}>Find reliable workers from verified labour associations.</Text>

        <View style={styles.illustrationWrap}>
          <SkylineIllustration tone="blue" height={70} showFigures={false} />
        </View>
      </View>

      <View style={styles.searchWrap}>
        <View style={styles.searchBox}>
          <Ionicons name="search" size={18} color={colors.textMuted} />
          <TextInput
            style={styles.searchInput}
            placeholder="Search for a service..."
            placeholderTextColor={colors.textMuted}
            value={query}
            onChangeText={setQuery}
            autoCapitalize="none"
            autoCorrect={false}
          />
          {query.length > 0 ? (
            <Pressable onPress={() => setQuery('')} accessibilityLabel="Clear search">
              <Ionicons name="close" size={18} color={colors.textMuted} />
            </Pressable>
          ) : null}
        </View>
      </View>

      {isSearching ? (
        <FlatList
          key="search-results"
          contentContainerStyle={styles.listContent}
          data={results}
          keyExtractor={(item) => item.id}
          ListHeaderComponent={
            <View style={styles.sectionHeaderRow}>
              <Text style={styles.sectionHeading}>Services</Text>
              <Text style={styles.resultCount}>{results.length} results</Text>
            </View>
          }
          renderItem={({ item, index }) => (
            <View style={styles.listItemSpacing}>
              <ServiceCard
                service={item}
                variant="list"
                tintIndex={index}
                onPress={() => handleSelectService(item)}
              />
            </View>
          )}
          ListEmptyComponent={
            <View style={styles.emptyState}>
              <View style={styles.emptyIconWrap}>
                <Ionicons name="search" size={26} color={colors.textMuted} />
              </View>
              <Text style={styles.emptyTitle}>No services found</Text>
              <Text style={styles.emptyBody}>
                No matching services for &quot;{query.trim()}&quot;.{'\n'}Try a different keyword or browse all
                services.
              </Text>
              <Pressable style={styles.emptyAction} onPress={() => setQuery('')}>
                <Text style={styles.emptyActionText}>View All Services</Text>
                <Ionicons name="chevron-forward" size={16} color={colors.blue} />
              </Pressable>
            </View>
          }
          ListFooterComponent={
            results.length > 0 ? (
              <View style={styles.canFindWrap}>
                <Text style={styles.canFindTitle}>Can&apos;t find what you&apos;re looking for?</Text>
                <Text style={styles.canFindBody}>Try a different keyword or browse all services.</Text>
                <Pressable style={styles.viewAllButton} onPress={() => setQuery('')}>
                  <Text style={styles.viewAllButtonText}>View All Services</Text>
                  <Ionicons name="chevron-forward" size={16} color={colors.blue} />
                </Pressable>
              </View>
            ) : null
          }
        />
      ) : (
        <FlatList
          key="popular-grid"
          contentContainerStyle={styles.listContent}
          data={popular}
          numColumns={3}
          columnWrapperStyle={styles.gridRow}
          keyExtractor={(item) => item.id}
          ListHeaderComponent={
            <View style={styles.sectionHeaderRow}>
              <Text style={styles.sectionHeading}>Popular Services</Text>
            </View>
          }
          renderItem={({ item, index }) => (
            <ServiceCard service={item} variant="grid" tintIndex={index} onPress={() => handleSelectService(item)} />
          )}
          ListFooterComponent={
            <View style={styles.infoCard}>
              <Ionicons name="shield-checkmark" size={20} color={colors.blue} />
              <Text style={styles.infoText}>All workers are verified through registered labour associations.</Text>
            </View>
          }
        />
      )}

      <BottomNavBar
        active="book"
        onNavigateHome={() => router.replace('/(user)/home')}
        onNavigateRequests={() => router.push('/(user)/ongoing-requests')}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: colors.white,
  },
  headerBanner: {
    backgroundColor: colors.blueTint,
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.xl,
    paddingBottom: spacing.sm,
    overflow: 'hidden',
  },
  headerRow: {
    marginBottom: spacing.md,
  },
  title: {
    ...typography.heading,
    fontSize: 22,
  },
  subtitle: {
    ...typography.subheading,
    marginTop: 4,
    maxWidth: '85%',
  },
  illustrationWrap: {
    marginTop: spacing.sm,
    marginHorizontal: -spacing.lg,
  },
  searchWrap: {
    paddingHorizontal: spacing.lg,
    marginTop: spacing.md,
    marginBottom: spacing.sm,
  },
  searchBox: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    backgroundColor: colors.white,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.pill,
    paddingHorizontal: spacing.md,
    paddingVertical: 12,
    shadowColor: '#000',
    shadowOpacity: 0.04,
    shadowRadius: 6,
    shadowOffset: { width: 0, height: 2 },
    elevation: 1,
  },
  searchInput: {
    flex: 1,
    fontSize: 14,
    color: colors.navy,
  },
  listContent: {
    paddingHorizontal: spacing.lg,
    paddingBottom: spacing.lg,
    flexGrow: 1,
  },
  sectionHeaderRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.sm,
  },
  sectionHeading: {
    fontSize: 16,
    fontWeight: '800',
    color: colors.navy,
  },
  resultCount: {
    fontSize: 12,
    color: colors.textSecondary,
  },
  gridRow: {
    justifyContent: 'space-between',
    marginBottom: spacing.sm,
  },
  listItemSpacing: {
    marginBottom: spacing.sm,
  },
  infoCard: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: spacing.sm,
    backgroundColor: colors.blueTint,
    borderRadius: radius.md,
    padding: spacing.md,
    marginTop: spacing.md,
  },
  infoText: {
    flex: 1,
    fontSize: 12,
    color: colors.navy,
    lineHeight: 17,
  },
  emptyState: {
    alignItems: 'center',
    paddingVertical: spacing.xl,
    paddingHorizontal: spacing.lg,
  },
  emptyIconWrap: {
    width: 56,
    height: 56,
    borderRadius: radius.pill,
    backgroundColor: colors.background,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: spacing.md,
  },
  emptyTitle: {
    fontSize: 16,
    fontWeight: '800',
    color: colors.navy,
    marginBottom: spacing.xs,
  },
  emptyBody: {
    fontSize: 13,
    color: colors.textSecondary,
    textAlign: 'center',
    lineHeight: 19,
    marginBottom: spacing.lg,
  },
  emptyAction: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
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
  canFindWrap: {
    marginTop: spacing.md,
    paddingTop: spacing.md,
    borderTopWidth: 1,
    borderTopColor: colors.border,
  },
  canFindTitle: {
    fontSize: 14,
    fontWeight: '700',
    color: colors.navy,
    marginBottom: 2,
  },
  canFindBody: {
    fontSize: 12,
    color: colors.textSecondary,
    marginBottom: spacing.md,
  },
  viewAllButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 4,
    borderWidth: 1,
    borderColor: colors.blue,
    borderRadius: radius.pill,
    paddingVertical: 10,
  },
  viewAllButtonText: {
    color: colors.blue,
    fontWeight: '700',
    fontSize: 13,
  },
});
