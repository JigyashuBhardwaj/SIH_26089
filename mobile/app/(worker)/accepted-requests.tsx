import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { colors, spacing, typography } from '../../constants/theme';

/**
 * Reachable from Worker Home "Accepted Requests" card. Real detail view
 * (work/date/time/address, open in Maps, mark completed, QR collection)
 * is built in Phase 6 — this screen only proves the navigation entry
 * point exists.
 */
export default function AcceptedRequestsScreen() {
  const router = useRouter();

  return (
    <View style={styles.container}>
      <Pressable style={styles.backButton} onPress={() => router.back()}>
        <Ionicons name="arrow-back" size={22} color={colors.navy} />
      </Pressable>
      <View style={styles.center}>
        <Ionicons name="checkmark-done-outline" size={40} color={colors.green} />
        <Text style={styles.title}>Accepted Requests</Text>
        <Text style={styles.subtitle}>Job detail, Maps link, and completion flow are built in Phase 6.</Text>
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
