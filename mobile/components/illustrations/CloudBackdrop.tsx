import { StyleSheet, View } from 'react-native';
import { colors } from '../../constants/theme';

/**
 * Soft cloud silhouettes for the top of illustrated screens (splash and
 * login backgrounds). Three overlapping rounded shapes at low opacity —
 * built from plain Views, no image assets or SVG library needed.
 */
export function CloudBackdrop() {
  return (
    <View style={styles.container} pointerEvents="none">
      <View style={[styles.cloud, styles.cloudLarge, { top: 8, left: -30 }]} />
      <View style={[styles.cloud, styles.cloudMedium, { top: 36, right: -20 }]} />
      <View style={[styles.cloud, styles.cloudSmall, { top: 82, left: 48 }]} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    height: 150,
    overflow: 'hidden',
  },
  cloud: {
    position: 'absolute',
    backgroundColor: colors.white,
    opacity: 0.6,
    borderRadius: 999,
  },
  cloudLarge: { width: 150, height: 48 },
  cloudMedium: { width: 108, height: 36 },
  cloudSmall: { width: 74, height: 26 },
});
