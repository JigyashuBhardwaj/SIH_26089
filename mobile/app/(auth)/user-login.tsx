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
import { ComingSoonDialog } from '../../components/ComingSoonDialog';
import { CloudBackdrop } from '../../components/illustrations/CloudBackdrop';
import { SkylineIllustration } from '../../components/illustrations/SkylineIllustration';
import { KarmanyaLogo } from '../../components/KarmanyaLogo';
import { useAuth } from '../../features/auth';
import { useComingSoon } from '../../hooks/useComingSoon';
import { colors, radius, spacing, typography } from '../../constants/theme';

export default function UserLoginScreen() {
  const router = useRouter();
  const { loginAsUser, isAuthenticating } = useAuth();
  const comingSoon = useComingSoon();

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [passwordVisible, setPasswordVisible] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleLogin = async () => {
    setError(null);
    if (!username.trim() || !password) {
      setError('Please enter both username and password.');
      return;
    }
    try {
      await loginAsUser(username.trim(), password);
      router.replace('/(user)/home');
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

        <Text style={styles.heading}>Welcome Back!</Text>
        <Text style={styles.subheading}>Login to continue as a User</Text>

        <View style={styles.form}>
          <View style={styles.inputWrap}>
            <Ionicons name="person-outline" size={18} color={colors.textMuted} style={styles.inputIcon} />
            <TextInput
              style={styles.input}
              placeholder="Username"
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

          <Pressable style={styles.forgotLink} onPress={comingSoon.show}>
            <Text style={styles.forgotLinkText}>Forgot Password?</Text>
          </Pressable>

          {error ? <Text style={styles.error}>{error}</Text> : null}

          <Pressable style={styles.loginButton} onPress={handleLogin} disabled={isAuthenticating}>
            {isAuthenticating ? (
              <ActivityIndicator color={colors.white} />
            ) : (
              <Text style={styles.loginButtonText}>Login</Text>
            )}
          </Pressable>

          <Pressable style={styles.signUpRow} onPress={comingSoon.show}>
            <Text style={styles.signUpText}>
              Don&apos;t have an account? <Text style={styles.signUpLink}>Sign Up</Text>
            </Text>
          </Pressable>
        </View>

        <View style={styles.trustRow}>
          <Ionicons name="shield-checkmark-outline" size={16} color={colors.textSecondary} />
          <Text style={styles.trustText}>Safe. Simple. Reliable.</Text>
        </View>

        <View style={styles.illustrationWrap}>
          <SkylineIllustration tone="blue" height={130} />
        </View>

        <Text style={styles.demoHint}>Demo: demo_user / user123</Text>

        <ComingSoonDialog visible={comingSoon.visible} onDismiss={comingSoon.dismiss} />
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
  forgotLink: {
    alignSelf: 'flex-end',
  },
  forgotLinkText: {
    color: colors.blue,
    fontSize: 13,
    fontWeight: '600',
  },
  error: {
    color: colors.danger,
    textAlign: 'center',
    fontSize: 13,
  },
  loginButton: {
    backgroundColor: colors.blue,
    paddingVertical: 14,
    borderRadius: radius.pill,
    alignItems: 'center',
  },
  loginButtonText: {
    color: colors.white,
    fontWeight: '700',
    fontSize: 16,
  },
  signUpRow: {
    alignItems: 'center',
    marginTop: spacing.xs,
  },
  signUpText: {
    fontSize: 13,
    color: colors.textSecondary,
  },
  signUpLink: {
    color: colors.blue,
    fontWeight: '700',
  },
  trustRow: {
    marginTop: spacing.xl,
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    gap: spacing.xs,
  },
  trustText: {
    fontSize: 12,
    color: colors.textSecondary,
  },
  illustrationWrap: {
    marginTop: spacing.md,
  },
  demoHint: {
    textAlign: 'center',
    opacity: 0.5,
    fontSize: 11,
    marginTop: spacing.sm,
  },
});
