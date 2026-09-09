import { Ionicons } from '@expo/vector-icons';
import { StyleSheet, Text, View } from 'react-native';
import { colors } from '../constants/theme';

interface KarmanyaLogoProps {
  /** 'large' for the splash screen, 'compact' for header use on other screens. */
  size?: 'large' | 'compact';
  showTagline?: boolean;
}

/**
 * The two-figure mark plus "KARMANYA" wordmark seen across every reference
 * screen. Built from vector icons/text rather than a bitmap asset so it
 * scales cleanly and needs no image files.
 */
export function KarmanyaLogo({ size = 'compact', showTagline = true }: KarmanyaLogoProps) {
  const isLarge = size === 'large';
  const iconSize = isLarge ? 56 : 34;

  return (
    <View style={styles.container}>
      <View style={[styles.markRow, { marginBottom: isLarge ? 12 : 6 }]}>
        <Ionicons name="body" size={iconSize} color={colors.green} style={styles.markLeft} />
        <Ionicons name="body" size={iconSize} color={colors.blue} style={styles.markRight} />
      </View>
      <Text style={[styles.title, isLarge && styles.titleLarge]}>KARMANYA</Text>
      {showTagline ? <Text style={styles.tagline}>People · Work · Stronger Communities</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
  },
  markRow: {
    flexDirection: 'row',
  },
  markLeft: {
    marginRight: -10,
    transform: [{ rotate: '-8deg' }],
  },
  markRight: {
    marginLeft: -10,
    transform: [{ rotate: '8deg' }],
  },
  title: {
    fontSize: 20,
    fontWeight: '800',
    color: colors.navy,
    letterSpacing: 1,
  },
  titleLarge: {
    fontSize: 30,
  },
  tagline: {
    marginTop: 2,
    fontSize: 10,
    fontWeight: '600',
    color: colors.textSecondary,
    letterSpacing: 1,
    textTransform: 'uppercase',
  },
});
