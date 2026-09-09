import { useRouter } from 'expo-router';
import { StyleSheet, Text, View } from 'react-native';
import { SkylineIllustration } from '../components/illustrations/SkylineIllustration';
import { KarmanyaLogo } from '../components/KarmanyaLogo';
import { RoleCard } from '../components/RoleCard';
import { colors, spacing, typography } from '../constants/theme';

export default function RoleSelectionScreen() {
  const router = useRouter();

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <KarmanyaLogo size="compact" />
      </View>

      <Text style={styles.heading}>How would you like to continue?</Text>

      <View style={styles.cards}>
        <RoleCard
          icon="person-outline"
          title="Login / Sign Up as User"
          subtitle="Find. Book. Get Things Done."
          accent="blue"
          onPress={() => router.push('/(auth)/user-login')}
        />
        <RoleCard
          icon="hammer-outline"
          title="Login as Worker"
          subtitle="Get Work. Grow. Build. Communities."
          accent="green"
          onPress={() => router.push('/(auth)/worker-login')}
        />
      </View>

      <View style={styles.illustrationWrap}>
        <SkylineIllustration tone="mixed" height={150} />
        <Text style={styles.footerText}>Together for a better tomorrow.</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.white,
    padding: spacing.lg,
    paddingTop: spacing.xxl,
  },
  header: {
    alignItems: 'center',
    marginBottom: spacing.lg,
  },
  heading: {
    ...typography.heading,
    textAlign: 'center',
    marginBottom: spacing.lg,
  },
  cards: {
    justifyContent: 'center',
  },
  illustrationWrap: {
    marginTop: 'auto',
  },
  footerText: {
    textAlign: 'center',
    fontSize: 12,
    color: colors.textSecondary,
    marginTop: spacing.sm,
  },
});
