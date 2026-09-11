import { StyleSheet, View } from 'react-native';
import { colors } from '../../constants/theme';
import { WorkerSilhouette } from './WorkerSilhouette';

interface SkylineIllustrationProps {
  /** Bias the silhouette tones toward the User (blue) or Worker (green) identity. */
  tone?: 'blue' | 'green' | 'mixed';
  height?: number;
  /** Set false for a compact skyline-only banner (no worker figures in front). Defaults to true, unchanged for existing screens. */
  showFigures?: boolean;
}

const BUILDING_HEIGHTS = [34, 58, 42, 72, 50, 64, 38, 56, 46];

/**
 * The illustrated "community/skyline" band that runs along the bottom of
 * the splash, role-selection, and login screens in the reference design:
 * a row of buildings with a small crowd of worker silhouettes standing in
 * front of them. Built entirely from Views (rectangles for buildings,
 * composed shapes for the figures) — no illustration assets or SVG
 * library, per the "no new illustration dependency" constraint. Sized
 * and weighted to read as a real illustrated section, not a thin
 * decorative strip.
 */
export function SkylineIllustration({ tone = 'mixed', height = 132, showFigures = true }: SkylineIllustrationProps) {
  const figureColor = tone === 'blue' ? colors.blue : tone === 'green' ? colors.green : colors.primaryBlue;

  return (
    <View style={[styles.container, { height }]} pointerEvents="none">
      <View style={styles.buildings}>
        {BUILDING_HEIGHTS.map((h, index) => (
          <View
            key={index}
            style={[
              styles.building,
              { height: h, backgroundColor: colors.skyline, opacity: 0.6 + (index % 3) * 0.12 },
            ]}
          />
        ))}
      </View>
      <View style={styles.groundLine} />
      {showFigures ? (
        <View style={styles.figures}>
          <WorkerSilhouette color={figureColor} height={46} hardHat />
          <WorkerSilhouette color={figureColor} height={38} />
          <WorkerSilhouette color={figureColor} height={50} hardHat hatColor={colors.hardHat} />
          <WorkerSilhouette color={figureColor} height={36} />
          <WorkerSilhouette color={figureColor} height={44} hardHat />
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    justifyContent: 'flex-end',
  },
  buildings: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    justifyContent: 'space-evenly',
    height: '62%',
  },
  building: {
    width: 24,
    borderTopLeftRadius: 3,
    borderTopRightRadius: 3,
  },
  groundLine: {
    height: 2,
    backgroundColor: colors.border,
  },
  figures: {
    flexDirection: 'row',
    justifyContent: 'space-evenly',
    alignItems: 'flex-end',
    paddingTop: 6,
  },
});
