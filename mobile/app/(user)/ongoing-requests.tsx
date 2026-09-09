import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { colors, spacing, typography } from '../../constants/theme';

/**
 * Reachable from the User Home "Ongoing Requests" card. Real request
 * tracking (worker info, contact, cancel, confirm, pay, rate) needs the
 * booking flow and backend from Phase 3/4/7 — this screen only proves the
 * navigation entry point exists.
 */
export default function OngoingRequestsScreen() {
  const router = useRouter();

  return (
    <View style={styles.container}>
      <Pressable style={styles.backButton} onPress={() => router.back()}>
        <Ionicons name="arrow-back" size={22} color={colors.navy} />
      </Pressable>
      <View style={styles.center}>
        <Ionicons name="time-outline" size={40} color={colors.blue} />
        <Text style={styles.title}>Ongoing Requests</Text>
        <Text style={styles.subtitle}>Live request tracking is built in Phase 3/7.</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.white, padding: spacing.lg, paddingTop: spacing.xl },
  backButton: { marginBottom: spacing.md },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: spacing.sm },
  title: { ...typography.heading, fontSize: 20 },
  subtitle: { ...typography.subheading, textAlign: 'center' },
});
