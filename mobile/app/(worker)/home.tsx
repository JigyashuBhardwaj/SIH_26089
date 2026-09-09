import { useRouter } from 'expo-router';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { ComingSoonDialog } from '../../components/ComingSoonDialog';
import { FeatureCard } from '../../components/FeatureCard';
import { KarmanyaLogo } from '../../components/KarmanyaLogo';
import { ProfileMenu } from '../../components/ProfileMenu';
import { useAuth } from '../../features/auth';
import { useComingSoon } from '../../hooks/useComingSoon';
import { colors, spacing } from '../../constants/theme';

export default function WorkerHomeScreen() {
  const router = useRouter();
  const { session, logout } = useAuth();
  const comingSoon = useComingSoon();

  const displayName = session?.displayName ?? 'Worker';

  const handleLogout = () => {
    logout();
    router.replace('/role-selection');
  };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <View style={styles.header}>
        <View>
          <KarmanyaLogo size="compact" showTagline={false} />
          <Text style={styles.greeting}>Hi, {displayName} 👋</Text>
        </View>
        <ProfileMenu name={displayName} roleLabel="Worker" onLogout={handleLogout} />
      </View>

      <View style={styles.grid}>
        <FeatureCard
          icon="briefcase-outline"
          title="Booking Requests"
          variant="active"
          accent="green"
          onPress={() => router.push('/(worker)/requests')}
        />
        <FeatureCard
          icon="checkmark-done-outline"
          title="Accepted Requests"
          variant="active"
          accent="green"
          onPress={() => router.push('/(worker)/accepted-requests')}
        />
        <FeatureCard icon="calendar-outline" title="Set Availability" onPress={comingSoon.show} />
        <FeatureCard icon="airplane-outline" title="Apply Leave" onPress={comingSoon.show} />
        <FeatureCard icon="headset-outline" title="Contact Support" onPress={comingSoon.show} />
      </View>

      <ComingSoonDialog visible={comingSoon.visible} onDismiss={comingSoon.dismiss} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flexGrow: 1,
    backgroundColor: colors.background,
    padding: spacing.lg,
    paddingTop: spacing.xl,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: spacing.lg,
  },
  greeting: {
    marginTop: spacing.sm,
    fontSize: 18,
    fontWeight: '700',
    color: colors.navy,
  },
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.md,
  },
});
