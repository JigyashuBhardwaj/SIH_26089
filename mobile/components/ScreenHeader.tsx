import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { Pressable, StyleSheet, View } from 'react-native';
import { KarmanyaLogo } from './KarmanyaLogo';
import { ProfileMenu } from './ProfileMenu';
import { colors, spacing } from '../constants/theme';

interface ScreenHeaderProps {
  profileName: string;
  profileRoleLabel: string;
  onLogout: () => void;
}

/**
 * Back button + KARMANYA logo + profile menu in one row — used on Phase 3+
 * sub-screens that sit below Home (Home itself has no back button, so it
 * doesn't use this). Composed entirely from the existing KarmanyaLogo and
 * ProfileMenu components; this is not a new header design, just a new
 * arrangement of the same approved pieces for screens that need a back
 * action.
 */
export function ScreenHeader({ profileName, profileRoleLabel, onLogout }: ScreenHeaderProps) {
  const router = useRouter();

  return (
    <View style={styles.row}>
      <Pressable
        style={styles.iconButton}
        onPress={() => router.back()}
        accessibilityLabel="Go back"
        accessibilityRole="button"
      >
        <Ionicons name="arrow-back" size={22} color={colors.navy} />
      </Pressable>

      <KarmanyaLogo size="compact" showTagline />

      <ProfileMenu name={profileName} roleLabel={profileRoleLabel} onLogout={onLogout} />
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  iconButton: {
    padding: spacing.xs,
  },
});
