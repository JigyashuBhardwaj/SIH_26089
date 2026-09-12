import { Ionicons } from '@expo/vector-icons';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { colors, spacing, typography } from '../../constants/theme';

/**
 * Reachable from Schedule Date & Time after a valid date/time is chosen.
 * This is the minimum needed to give Phase 3B's Continue button a real
 * destination and prove the service + date/time selections are carried
 * forward. Actual association selection is Phase 3C, not this screen.
 */
export default function SelectAssociationScreen() {
  const router = useRouter();
  const { serviceName, dateTimeLabel } = useLocalSearchParams<{
    serviceId?: string;
    serviceName?: string;
    dateTimeLabel?: string;
  }>();

  return (
    <View style={styles.container}>
      <Pressable style={styles.backButton} onPress={() => router.back()}>
        <Ionicons name="arrow-back" size={22} color={colors.navy} />
      </Pressable>
      <View style={styles.center}>
        <Ionicons name="people-outline" size={40} color={colors.blue} />
        <Text style={styles.title}>Select Association</Text>
        {serviceName ? <Text style={styles.selected}>Service: {serviceName}</Text> : null}
        {dateTimeLabel ? <Text style={styles.selected}>When: {dateTimeLabel}</Text> : null}
        <Text style={styles.subtitle}>Cooperative labour association selection is built in Phase 3C.</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.white, padding: spacing.lg, paddingTop: spacing.xl },
  backButton: { marginBottom: spacing.md },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: spacing.sm },
  title: { ...typography.heading, fontSize: 20 },
  selected: { fontSize: 14, fontWeight: '700', color: colors.blue },
  subtitle: { ...typography.subheading, textAlign: 'center' },
});
