import { useRouter } from 'expo-router';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { ComingSoonDialog } from '../../components/ComingSoonDialog';
import { FeatureCard } from '../../components/FeatureCard';
import { KarmanyaLogo } from '../../components/KarmanyaLogo';
import { ProfileMenu } from '../../components/ProfileMenu';
import { useAuth } from '../../features/auth';
import { useComingSoon } from '../../hooks/useComingSoon';
import { colors, spacing } from '../../constants/theme';

// Locked product requirement for this MVP checkpoint: the demo User Home
// greets "Madhav" regardless of what was typed on the login screen.
const USER_DISPLAY_NAME = 'Madhav';

export default function UserHomeScreen() {
  const router = useRouter();
  const { logout } = useAuth();
  const comingSoon = useComingSoon();

  const handleLogout = () => {
    logout();
    router.replace('/role-selection');
  };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <View style={styles.header}>
        <View>
          <KarmanyaLogo size="compact" showTagline={false} />
          <Text style={styles.greeting}>Hi, {USER_DISPLAY_NAME} 👋</Text>
        </View>
        <ProfileMenu name={USER_DISPLAY_NAME} roleLabel="User" onLogout={handleLogout} />
      </View>

      <View style={styles.grid}>
        <FeatureCard
          icon="add-circle-outline"
          title="Book a Service"
          variant="active"
          accent="blue"
          onPress={() => router.push('/(user)/book-service')}
        />
        <FeatureCard
          icon="time-outline"
          title="Ongoing Requests"
          variant="active"
          accent="blue"
          onPress={() => router.push('/(user)/ongoing-requests')}
        />
        <FeatureCard icon="document-text-outline" title="Booking History" onPress={comingSoon.show} />
        <FeatureCard icon="alert-circle-outline" title="Emergency Booking" onPress={comingSoon.show} />
        <FeatureCard icon="people-outline" title="Book for Someone Else" onPress={comingSoon.show} />
        <FeatureCard icon="heart-outline" title="Donate to Charity" onPress={comingSoon.show} />
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
