import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { colors, spacing, typography } from '../../constants/theme';

/**
 * Reachable from the User Home "Book a Service" card. The actual booking
 * workflow (category/work selection, date/time, address, association,
 * summary) is Phase 3 — this screen only proves the navigation entry
 * point exists.
 */
export default function BookServiceScreen() {
  const router = useRouter();

  return (
    <View style={styles.container}>
      <Pressable style={styles.backButton} onPress={() => router.back()}>
        <Ionicons name="arrow-back" size={22} color={colors.navy} />
      </Pressable>
      <View style={styles.center}>
        <Ionicons name="add-circle-outline" size={40} color={colors.blue} />
        <Text style={styles.title}>Book a Service</Text>
        <Text style={styles.subtitle}>The full booking workflow is built in Phase 3.</Text>
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
