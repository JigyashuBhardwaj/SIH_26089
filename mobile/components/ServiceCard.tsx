import { Ionicons } from '@expo/vector-icons';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { colors, radius, spacing } from '../constants/theme';
import type { CatalogService } from '../services/serviceCatalog';

interface ServiceCardProps {
  service: CatalogService;
  variant: 'grid' | 'list';
  /** Alternates the tile tint between blue/green so the grid isn't monotone, without inventing new colors. */
  tintIndex?: number;
  onPress: () => void;
}

export function ServiceCard({ service, variant, tintIndex = 0, onPress }: ServiceCardProps) {
  const useGreen = tintIndex % 2 === 1;
  const tint = useGreen ? colors.greenTint : colors.blueTint;
  const accent = useGreen ? colors.green : colors.blue;

  if (variant === 'grid') {
    return (
      <Pressable style={styles.gridCard} onPress={onPress} accessibilityRole="button">
        <View style={[styles.gridIconWrap, { backgroundColor: tint }]}>
          <Ionicons name={service.icon} size={26} color={accent} />
        </View>
        <Text style={styles.gridLabel} numberOfLines={1}>
          {service.name}
        </Text>
      </Pressable>
    );
  }

  return (
    <Pressable style={styles.listCard} onPress={onPress} accessibilityRole="button">
      <View style={[styles.listIconWrap, { backgroundColor: tint }]}>
        <Ionicons name={service.icon} size={22} color={accent} />
      </View>
      <View style={styles.listTextWrap}>
        <Text style={styles.listTitle}>{service.name}</Text>
        {service.description ? (
          <Text style={styles.listDescription} numberOfLines={2}>
            {service.description}
          </Text>
        ) : null}
      </View>
      <Ionicons name="chevron-forward" size={18} color={colors.textMuted} />
    </Pressable>
  );
}

const styles = StyleSheet.create({
  gridCard: {
    width: '31%',
    backgroundColor: colors.white,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    paddingVertical: spacing.md,
    alignItems: 'center',
    gap: spacing.sm,
  },
  gridIconWrap: {
    width: 52,
    height: 52,
    borderRadius: radius.md,
    alignItems: 'center',
    justifyContent: 'center',
  },
  gridLabel: {
    fontSize: 12,
    fontWeight: '700',
    color: colors.navy,
  },
  listCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.white,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    padding: spacing.md,
    gap: spacing.md,
  },
  listIconWrap: {
    width: 44,
    height: 44,
    borderRadius: radius.sm,
    alignItems: 'center',
    justifyContent: 'center',
  },
  listTextWrap: {
    flex: 1,
  },
  listTitle: {
    fontSize: 14,
    fontWeight: '700',
    color: colors.navy,
  },
  listDescription: {
    fontSize: 12,
    color: colors.textSecondary,
    marginTop: 2,
  },
});
