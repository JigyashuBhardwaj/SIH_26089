import { Ionicons } from '@expo/vector-icons';
import DateTimePicker, { type DateTimePickerChangeEvent } from '@react-native-community/datetimepicker';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useMemo, useState } from 'react';
import { Platform, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { BottomNavBar } from '../../components/BottomNavBar';
import { ScreenHeader } from '../../components/ScreenHeader';
import { useAuth } from '../../features/auth';
import { colors, radius, spacing, typography } from '../../constants/theme';
import { isServiceTimeValid, MIN_BOOKING_LEAD_TIME_HOURS } from '@shared/booking';

function formatDateLabel(date: Date): string {
  return date.toLocaleDateString(undefined, {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  });
}

function formatTimeLabel(date: Date): string {
  return date.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit', hour12: true });
}

/** Combines a date-only value and a time-only value into one Date. */
function combineDateAndTime(date: Date, time: Date): Date {
  const combined = new Date(date);
  combined.setHours(time.getHours(), time.getMinutes(), 0, 0);
  return combined;
}

/**
 * Phase 3B — lets the person choose when they need the selected service.
 * The selected service comes from Phase 3A via route params; this screen
 * never creates or looks up a service itself. The 4-hour minimum lead
 * time is enforced for real (see shared/booking/bookingRules.ts), not
 * just described in text — Continue is disabled until it's satisfied.
 */
export default function ScheduleScreen() {
  const router = useRouter();
  const { session, logout } = useAuth();
  const { serviceId, serviceName } = useLocalSearchParams<{ serviceId?: string; serviceName?: string }>();

  const [selectedDate, setSelectedDate] = useState<Date | null>(null);
  const [selectedTime, setSelectedTime] = useState<Date | null>(null);
  const [showDatePicker, setShowDatePicker] = useState(false);
  const [showTimePicker, setShowTimePicker] = useState(false);

  const hasService = Boolean(serviceId && serviceName);

  const combinedDateTime = useMemo(() => {
    if (!selectedDate || !selectedTime) return null;
    return combineDateAndTime(selectedDate, selectedTime);
  }, [selectedDate, selectedTime]);

  // Real enforcement, not just a UI hint: recomputed against the device's
  // actual current time whenever the selection changes.
  const isDateTimeValid = useMemo(() => {
    if (!combinedDateTime) return false;
    return isServiceTimeValid(new Date(), combinedDateTime);
  }, [combinedDateTime]);

  const showInvalidMessage = combinedDateTime !== null && !isDateTimeValid;

  const handleLogout = () => {
    logout();
    router.replace('/role-selection');
  };

  const handleDateChange = (_event: DateTimePickerChangeEvent, date: Date) => {
    setSelectedDate(date);
    setShowDatePicker(Platform.OS === 'ios');
  };

  const handleDateDismiss = () => {
    setShowDatePicker(false);
  };

  const handleTimeChange = (_event: DateTimePickerChangeEvent, time: Date) => {
    setSelectedTime(time);
    setShowTimePicker(Platform.OS === 'ios');
  };

  const handleTimeDismiss = () => {
    setShowTimePicker(false);
  };

  const handleContinue = () => {
    if (!hasService || !combinedDateTime || !isDateTimeValid) return;
    router.push({
      pathname: '/(user)/select-association',
      params: {
        serviceId: serviceId as string,
        serviceName: serviceName as string,
        dateTimeLabel: `${formatDateLabel(combinedDateTime)}, ${formatTimeLabel(combinedDateTime)}`,
      },
    });
  };

  const canContinue = hasService && combinedDateTime !== null && isDateTimeValid;

  return (
    <View style={styles.screen}>
      <View style={styles.headerWrap}>
        <ScreenHeader
          profileName={session?.displayName ?? 'User'}
          profileRoleLabel="User"
          onLogout={handleLogout}
        />
      </View>

      <ScrollView contentContainerStyle={styles.content}>
        <Text style={styles.title}>Schedule Date &amp; Time</Text>
        <Text style={styles.subtitle}>Choose when you need the service.</Text>

        {hasService ? (
          <View style={styles.summaryCard}>
            <Text style={styles.summaryLabel}>Service</Text>
            <Text style={styles.summaryValue}>{serviceName}</Text>
          </View>
        ) : (
          <View style={styles.warningCard}>
            <Ionicons name="alert-circle-outline" size={18} color={colors.warning} />
            <Text style={styles.warningText}>
              No service was selected. Please go back and choose a service before scheduling.
            </Text>
          </View>
        )}

        <Pressable
          style={styles.selectorCard}
          onPress={() => setShowDatePicker(true)}
          disabled={!hasService}
        >
          <View style={styles.selectorIconWrap}>
            <Ionicons name="calendar-outline" size={20} color={colors.blue} />
          </View>
          <View style={styles.selectorTextWrap}>
            <Text style={styles.selectorLabel}>Date</Text>
            <Text style={styles.selectorValue}>{selectedDate ? formatDateLabel(selectedDate) : 'Select a date'}</Text>
          </View>
          <Ionicons name="chevron-forward" size={18} color={colors.textMuted} />
        </Pressable>

        <Pressable
          style={styles.selectorCard}
          onPress={() => setShowTimePicker(true)}
          disabled={!hasService}
        >
          <View style={styles.selectorIconWrap}>
            <Ionicons name="time-outline" size={20} color={colors.blue} />
          </View>
          <View style={styles.selectorTextWrap}>
            <Text style={styles.selectorLabel}>Time</Text>
            <Text style={styles.selectorValue}>{selectedTime ? formatTimeLabel(selectedTime) : 'Select a time'}</Text>
          </View>
          <Ionicons name="chevron-forward" size={18} color={colors.textMuted} />
        </Pressable>

        {showDatePicker ? (
          <DateTimePicker
            value={selectedDate ?? new Date()}
            mode="date"
            display={Platform.OS === 'ios' ? 'spinner' : 'default'}
            minimumDate={new Date()}
            onValueChange={handleDateChange}
            onDismiss={handleDateDismiss}
          />
        ) : null}

        {showTimePicker ? (
          <DateTimePicker
            value={selectedTime ?? new Date()}
            mode="time"
            display={Platform.OS === 'ios' ? 'spinner' : 'default'}
            onValueChange={handleTimeChange}
            onDismiss={handleTimeDismiss}
          />
        ) : null}

        {showInvalidMessage ? (
          <View style={styles.errorCard}>
            <Ionicons name="close-circle-outline" size={18} color={colors.error} />
            <Text style={styles.errorText}>Please choose a time at least 4 hours from now.</Text>
          </View>
        ) : (
          <View style={styles.infoCard}>
            <Ionicons name="information-circle-outline" size={18} color={colors.blue} />
            <Text style={styles.infoText}>
              Service requests require at least {MIN_BOOKING_LEAD_TIME_HOURS} hours notice.
            </Text>
          </View>
        )}

        <Pressable
          style={[styles.continueButton, !canContinue && styles.continueButtonDisabled]}
          onPress={handleContinue}
          disabled={!canContinue}
        >
          <Text style={styles.continueButtonText}>Continue</Text>
        </Pressable>
      </ScrollView>

      <BottomNavBar
        active="book"
        onNavigateHome={() => router.replace('/(user)/home')}
        onNavigateRequests={() => router.push('/(user)/ongoing-requests')}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: colors.white,
  },
  headerWrap: {
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.xl,
    paddingBottom: spacing.sm,
  },
  content: {
    paddingHorizontal: spacing.lg,
    paddingBottom: spacing.lg,
  },
  title: {
    ...typography.heading,
    fontSize: 22,
  },
  subtitle: {
    ...typography.subheading,
    marginTop: 4,
    marginBottom: spacing.lg,
  },
  summaryCard: {
    backgroundColor: colors.blueTint,
    borderRadius: radius.md,
    padding: spacing.md,
    marginBottom: spacing.lg,
  },
  summaryLabel: {
    fontSize: 12,
    color: colors.textSecondary,
    marginBottom: 2,
  },
  summaryValue: {
    fontSize: 16,
    fontWeight: '800',
    color: colors.navy,
  },
  warningCard: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: spacing.sm,
    backgroundColor: '#FEF6E7',
    borderWidth: 1,
    borderColor: colors.warning,
    borderRadius: radius.md,
    padding: spacing.md,
    marginBottom: spacing.lg,
  },
  warningText: {
    flex: 1,
    fontSize: 12,
    color: colors.navy,
    lineHeight: 17,
  },
  selectorCard: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    padding: spacing.md,
    marginBottom: spacing.md,
  },
  selectorIconWrap: {
    width: 40,
    height: 40,
    borderRadius: radius.sm,
    backgroundColor: colors.blueTint,
    alignItems: 'center',
    justifyContent: 'center',
  },
  selectorTextWrap: {
    flex: 1,
  },
  selectorLabel: {
    fontSize: 12,
    color: colors.textSecondary,
  },
  selectorValue: {
    fontSize: 14,
    fontWeight: '700',
    color: colors.navy,
    marginTop: 2,
  },
  infoCard: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: spacing.sm,
    backgroundColor: colors.blueTint,
    borderRadius: radius.md,
    padding: spacing.md,
    marginTop: spacing.xs,
    marginBottom: spacing.lg,
  },
  infoText: {
    flex: 1,
    fontSize: 12,
    color: colors.navy,
    lineHeight: 17,
  },
  errorCard: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: spacing.sm,
    backgroundColor: '#FCEBEB',
    borderWidth: 1,
    borderColor: colors.error,
    borderRadius: radius.md,
    padding: spacing.md,
    marginTop: spacing.xs,
    marginBottom: spacing.lg,
  },
  errorText: {
    flex: 1,
    fontSize: 12,
    color: colors.error,
    lineHeight: 17,
    fontWeight: '600',
  },
  continueButton: {
    backgroundColor: colors.blue,
    paddingVertical: 14,
    borderRadius: radius.pill,
    alignItems: 'center',
  },
  continueButtonDisabled: {
    backgroundColor: colors.border,
  },
  continueButtonText: {
    color: colors.white,
    fontWeight: '700',
    fontSize: 16,
  },
});
