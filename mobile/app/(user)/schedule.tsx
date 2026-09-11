import { Ionicons } from '@expo/vector-icons';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { colors, spacing, typography } from '../../constants/theme';

/**
 * Reachable from Book a Service after selecting a predefined service. This
 * is the minimum needed to prove the selection is preserved across the
 * navigation — actual date/time selection, the 4-hour lead-time rule, and
 * everything after it is a later Phase 3 step, not this one.
 */
export default function ScheduleScreen() {
  const router = useRouter();
  const { serviceName } = useLocalSearchParams<{ serviceId?: string; serviceName?: string }>();

  return (
    <View style={styles.container}>
      <Pressable style={styles.backButton} onPress={() => router.back()}>
        <Ionicons name="arrow-back" size={22} color={colors.navy} />
      </Pressable>
      <View style={styles.center}>
        <Ionicons name="calendar-outline" size={40} color={colors.blue} />
        <Text style={styles.title}>Schedule Date &amp; Time</Text>
        {serviceName ? <Text style={styles.selected}>Selected service: {serviceName}</Text> : null}
        <Text style={styles.subtitle}>Date/time selection and the 4-hour lead-time rule are built next in Phase 3.</Text>
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
