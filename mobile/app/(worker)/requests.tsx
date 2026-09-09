import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { colors, spacing, typography } from '../../constants/theme';

/**
 * Reachable from Worker Home "Booking Requests" card. Real accept/decline
 * functionality against live requests is built in Phase 6 — this screen
 * only proves the navigation entry point exists.
 */
export default function BookingRequestsScreen() {
  const router = useRouter();

  return (
    <View style={styles.container}>
      <Pressable style={styles.backButton} onPress={() => router.back()}>
        <Ionicons name="arrow-back" size={22} color={colors.navy} />
      </Pressable>
      <View style={styles.center}>
        <Ionicons name="briefcase-outline" size={40} color={colors.green} />
        <Text style={styles.title}>Booking Requests</Text>
        <Text style={styles.subtitle}>Accept/decline against live requests is built in Phase 6.</Text>
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
