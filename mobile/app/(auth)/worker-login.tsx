import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { useState } from 'react';
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { CloudBackdrop } from '../../components/illustrations/CloudBackdrop';
import { SkylineIllustration } from '../../components/illustrations/SkylineIllustration';
import { KarmanyaLogo } from '../../components/KarmanyaLogo';
import { useAuth } from '../../features/auth';
import { colors, radius, spacing, typography } from '../../constants/theme';

/**
 * Deliberately has no Sign Up option: worker accounts are provisioned by
 * the Federation/Association, never self-registered.
 */
export default function WorkerLoginScreen() {
  const router = useRouter();
  const { loginAsWorker, isAuthenticating } = useAuth();

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [passwordVisible, setPasswordVisible] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleLogin = async () => {
    setError(null);
    if (!username.trim() || !password) {
      setError('Please enter both Worker ID and password.');
      return;
    }
    try {
      await loginAsWorker(username.trim(), password);
      router.replace('/(worker)/home');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed.');
    }
  };

  return (
    <View style={styles.screen}>
      <CloudBackdrop />
      <ScrollView contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
        <Pressable style={styles.backButton} onPress={() => router.back()}>
          <Ionicons name="arrow-back" size={22} color={colors.navy} />
        </Pressable>

        <View style={styles.header}>
          <KarmanyaLogo size="compact" />
        </View>

        <Text style={styles.heading}>Worker Login</Text>
        <Text style={styles.subheading}>Login with your federation credentials</Text>

        <View style={styles.form}>
          <View style={styles.inputWrap}>
            <Ionicons name="person-outline" size={18} color={colors.textMuted} style={styles.inputIcon} />
            <TextInput
              style={styles.input}
              placeholder="Worker ID / Username"
              autoCapitalize="none"
              autoCorrect={false}
              value={username}
              onChangeText={setUsername}
            />
          </View>

          <View style={styles.inputWrap}>
            <Ionicons name="lock-closed-outline" size={18} color={colors.textMuted} style={styles.inputIcon} />
            <TextInput
              style={[styles.input, styles.inputFlex]}
              placeholder="Password"
              secureTextEntry={!passwordVisible}
              value={password}
              onChangeText={setPassword}
            />
            <Pressable onPress={() => setPasswordVisible((v) => !v)}>
              <Ionicons
                name={passwordVisible ? 'eye-off-outline' : 'eye-outline'}
                size={18}
                color={colors.textMuted}
              />
            </Pressable>
          </View>

          {error ? <Text style={styles.error}>{error}</Text> : null}

          <Pressable style={styles.loginButton} onPress={handleLogin} disabled={isAuthenticating}>
            {isAuthenticating ? (
              <ActivityIndicator color={colors.white} />
            ) : (
              <Text style={styles.loginButtonText}>Login</Text>
            )}
          </Pressable>

          <View style={styles.infoBox}>
            <Ionicons name="information-circle-outline" size={18} color={colors.green} />
            <Text style={styles.infoText}>
              Worker accounts are provided by your Labour Federation. Self-registration is not available.
            </Text>
          </View>
        </View>

        <View style={styles.illustrationWrap}>
          <SkylineIllustration tone="green" height={130} />
          <Text style={styles.footerText}>Skilled Workers{'\n'}Stronger Communities.</Text>
        </View>

        <Text style={styles.demoHint}>Demo: demo_worker / worker123</Text>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: colors.white,
  },
  container: {
    flexGrow: 1,
    padding: spacing.lg,
    paddingTop: spacing.xl,
  },
  backButton: {
    marginBottom: spacing.md,
  },
  header: {
    alignItems: 'center',
    marginBottom: spacing.lg,
  },
  heading: {
    ...typography.heading,
    textAlign: 'center',
  },
  subheading: {
    ...typography.subheading,
    textAlign: 'center',
    marginBottom: spacing.lg,
  },
  form: {
    gap: spacing.md,
  },
  inputWrap: {
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.pill,
    paddingHorizontal: spacing.md,
    paddingVertical: 12,
    gap: spacing.sm,
  },
  inputIcon: {
    marginRight: 2,
  },
  input: {
    flex: 1,
    fontSize: 14,
    color: colors.navy,
  },
  inputFlex: {
    marginRight: spacing.sm,
  },
  error: {
    color: colors.danger,
    textAlign: 'center',
    fontSize: 13,
  },
  loginButton: {
    backgroundColor: colors.green,
    paddingVertical: 14,
    borderRadius: radius.pill,
    alignItems: 'center',
  },
  loginButtonText: {
    color: colors.white,
    fontWeight: '700',
    fontSize: 16,
  },
  infoBox: {
    flexDirection: 'row',
    backgroundColor: colors.greenTint,
    borderWidth: 1,
    borderColor: colors.greenBorder,
    borderRadius: radius.md,
    padding: spacing.md,
    gap: spacing.sm,
    alignItems: 'flex-start',
  },
  infoText: {
    flex: 1,
    fontSize: 12,
    color: colors.greenDark,
    lineHeight: 17,
  },
  illustrationWrap: {
    marginTop: spacing.lg,
  },
  footerText: {
    marginTop: spacing.xl,
    textAlign: 'center',
    fontSize: 12,
    color: colors.textSecondary,
  },
  demoHint: {
    textAlign: 'center',
    opacity: 0.5,
    fontSize: 11,
    marginTop: spacing.md,
  },
});
