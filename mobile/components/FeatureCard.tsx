import { Ionicons } from '@expo/vector-icons';
import type { ComponentProps } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { colors, radius, spacing } from '../constants/theme';

interface FeatureCardProps {
  icon: ComponentProps<typeof Ionicons>['name'];
  title: string;
  onPress: () => void;
  /** Functional cards get the brand tint; non-functional ones stay neutral. */
  variant?: 'active' | 'neutral';
  accent?: 'blue' | 'green';
}

export function FeatureCard({ icon, title, onPress, variant = 'neutral', accent = 'blue' }: FeatureCardProps) {
  const isActive = variant === 'active';
  const accentColor = accent === 'green' ? colors.green : colors.blue;
  const tintColor = accent === 'green' ? colors.greenTint : colors.blueTint;

  return (
    <Pressable
      style={[styles.card, isActive && { backgroundColor: tintColor, borderColor: accentColor }]}
      onPress={onPress}
    >
      <View style={[styles.iconWrap, { backgroundColor: isActive ? colors.white : colors.background }]}>
        <Ionicons name={icon} size={22} color={isActive ? accentColor : colors.textSecondary} />
      </View>
      <Text style={[styles.title, isActive && { color: colors.navy }]}>{title}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {
    width: '47%',
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.sm,
    alignItems: 'flex-start',
    backgroundColor: colors.white,
  },
  iconWrap: {
    width: 40,
    height: 40,
    borderRadius: radius.sm,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: spacing.sm,
  },
  title: {
    fontSize: 13,
    fontWeight: '700',
    color: colors.textSecondary,
  },
});
