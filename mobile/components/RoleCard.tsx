import { Ionicons } from '@expo/vector-icons';
import type { ComponentProps } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { colors, radius, spacing } from '../constants/theme';

interface RoleCardProps {
  icon: ComponentProps<typeof Ionicons>['name'];
  title: string;
  subtitle: string;
  accent: 'blue' | 'green';
  onPress: () => void;
}

export function RoleCard({ icon, title, subtitle, accent, onPress }: RoleCardProps) {
  const accentColor = accent === 'green' ? colors.green : colors.blue;
  const tintColor = accent === 'green' ? colors.greenTint : colors.blueTint;
  const borderColor = accent === 'green' ? colors.greenBorder : colors.blueBorder;

  return (
    <Pressable
      style={[styles.card, { backgroundColor: tintColor, borderColor }]}
      onPress={onPress}
      accessibilityRole="button"
    >
      <View style={[styles.iconWrap, { backgroundColor: accentColor }]}>
        <Ionicons name={icon} size={22} color={colors.white} />
      </View>
      <View style={styles.textWrap}>
        <Text style={styles.title}>{title}</Text>
        <Text style={styles.subtitle}>{subtitle}</Text>
      </View>
      <Ionicons name="chevron-forward" size={20} color={colors.textMuted} />
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1,
    borderRadius: radius.lg,
    padding: spacing.md,
    marginBottom: spacing.md,
  },
  iconWrap: {
    width: 44,
    height: 44,
    borderRadius: radius.md,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: spacing.md,
  },
  textWrap: {
    flex: 1,
  },
  title: {
    fontSize: 16,
    fontWeight: '700',
    color: colors.navy,
  },
  subtitle: {
    fontSize: 12,
    color: colors.textSecondary,
    marginTop: 2,
  },
});
