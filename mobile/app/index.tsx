import { useRouter } from 'expo-router';
import { useEffect } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { CloudBackdrop } from '../components/illustrations/CloudBackdrop';
import { SkylineIllustration } from '../components/illustrations/SkylineIllustration';
import { KarmanyaLogo } from '../components/KarmanyaLogo';
import { colors, spacing } from '../constants/theme';

const SPLASH_DURATION_MS = 1600;

/**
 * KARMANYA splash screen. Shows briefly, then proceeds to Role Selection
 * on its own — there's nothing for the person to tap here.
 */
export default function SplashScreen() {
  const router = useRouter();

  useEffect(() => {
    const timer = setTimeout(() => {
      router.replace('/role-selection');
    }, SPLASH_DURATION_MS);
    return () => clearTimeout(timer);
  }, [router]);

  return (
    <View style={styles.container}>
      <CloudBackdrop />

      <View style={styles.center}>
        <KarmanyaLogo size="large" />
        <Text style={styles.heading}>Building{'\n'}Stronger Communities{'\n'}Together</Text>
      </View>

      <View style={styles.illustrationWrap}>
        <SkylineIllustration tone="mixed" height={190} />
      </View>

      <View style={styles.footer}>
        <View style={styles.progressTrack}>
          <View style={styles.progressFill} />
        </View>
        <Text style={styles.footerText}>Skilled Hands. Brighter Tomorrows.</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.blueTint,
    justifyContent: 'space-between',
    paddingTop: spacing.xxl,
    paddingBottom: spacing.lg,
  },
  center: {
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing.lg,
    paddingHorizontal: spacing.lg,
  },
  heading: {
    fontSize: 20,
    fontWeight: '700',
    color: colors.navy,
    textAlign: 'center',
    lineHeight: 28,
  },
  illustrationWrap: {
    marginTop: spacing.lg,
  },
  footer: {
    alignItems: 'center',
    gap: spacing.sm,
    paddingTop: spacing.sm,
  },
  progressTrack: {
    width: 120,
    height: 4,
    borderRadius: 2,
    backgroundColor: colors.blueBorder,
    overflow: 'hidden',
  },
  progressFill: {
    width: '55%',
    height: '100%',
    backgroundColor: colors.blue,
  },
  footerText: {
    fontSize: 12,
    color: colors.textSecondary,
    fontStyle: 'italic',
  },
});
