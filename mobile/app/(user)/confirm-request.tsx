import { Ionicons } from '@expo/vector-icons';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { colors, spacing, typography } from '../../constants/theme';

/**
 * Reachable from Select Association after choosing one. This is the
 * minimum needed to give Phase 3C's Continue button a real destination
 * and prove the service, date/time, and association selections are all
 * carried forward. Actual request confirmation/submission is Phase 3D,
 * not this screen.
 */
export default function ConfirmRequestScreen() {
  const router = useRouter();
  const { serviceName, dateTimeLabel, associationName } = useLocalSearchParams<{
    serviceId?: string;
    serviceName?: string;
    dateTimeLabel?: string;
    associationId?: string;
    associationName?: string;
  }>();

  return (
    <View style={styles.container}>
      <Pressable style={styles.backButton} onPress={() => router.back()}>
        <Ionicons name="arrow-back" size={22} color={colors.navy} />
      </Pressable>
      <View style={styles.center}>
        <Ionicons name="checkmark-circle-outline" size={40} color={colors.blue} />
        <Text style={styles.title}>Confirm Request</Text>
        {serviceName ? <Text style={styles.selected}>Service: {serviceName}</Text> : null}
        {dateTimeLabel ? <Text style={styles.selected}>When: {dateTimeLabel}</Text> : null}
        {associationName ? <Text style={styles.selected}>Association: {associationName}</Text> : null}
        <Text style={styles.subtitle}>Request confirmation and submission are built in Phase 3D.</Text>
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
