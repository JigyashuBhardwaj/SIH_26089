import { View } from 'react-native';

interface WorkerSilhouetteProps {
  color: string;
  height?: number;
  hardHat?: boolean;
  hatColor?: string;
}

/**
 * A deliberately simplified standing-person shape (head + torso + legs)
 * composed from plain Views. Several of these in a row stand in for the
 * "worker/community" figures along the bottom of the reference screens —
 * without needing an illustration asset or an SVG library.
 */
export function WorkerSilhouette({ color, height = 40, hardHat = false, hatColor = '#FBC02D' }: WorkerSilhouetteProps) {
  const headSize = height * 0.32;
  const bodyWidth = height * 0.36;
  const bodyHeight = height * 0.48;
  const legHeight = height * 0.28;

  return (
    <View style={{ alignItems: 'center', height, justifyContent: 'flex-end' }}>
      {hardHat ? (
        <View
          style={{
            width: headSize * 1.35,
            height: headSize * 0.55,
            backgroundColor: hatColor,
            borderTopLeftRadius: headSize,
            borderTopRightRadius: headSize,
            marginBottom: -headSize * 0.25,
          }}
        />
      ) : null}
      <View
        style={{
          width: headSize,
          height: headSize,
          borderRadius: headSize / 2,
          backgroundColor: color,
          marginBottom: 2,
        }}
      />
      <View
        style={{
          width: bodyWidth,
          height: bodyHeight,
          borderTopLeftRadius: bodyWidth / 2,
          borderTopRightRadius: bodyWidth / 2,
          backgroundColor: color,
        }}
      />
      <View style={{ flexDirection: 'row', gap: 3, marginTop: 1 }}>
        <View style={{ width: bodyWidth * 0.34, height: legHeight, backgroundColor: color, borderRadius: 3 }} />
        <View style={{ width: bodyWidth * 0.34, height: legHeight, backgroundColor: color, borderRadius: 3 }} />
      </View>
    </View>
  );
}
