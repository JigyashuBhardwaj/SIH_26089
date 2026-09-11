import { Ionicons } from '@expo/vector-icons';
import type { ComponentProps } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { colors, spacing } from '../constants/theme';

type NavKey = 'home' | 'book' | 'requests' | 'profile';

interface BottomNavBarProps {
  active: NavKey;
  onNavigateHome: () => void;
  onNavigateRequests: () => void;
}

interface NavItem {
  key: NavKey;
  label: string;
  icon: ComponentProps<typeof Ionicons>['name'];
}

const ITEMS: NavItem[] = [
  { key: 'home', label: 'Home', icon: 'home-outline' },
  { key: 'book', label: 'Book Service', icon: 'search' },
  { key: 'requests', label: 'My Requests', icon: 'chatbubble-ellipses-outline' },
  { key: 'profile', label: 'Profile', icon: 'person-outline' },
];

/**
 * The persistent bottom bar shown on User booking-flow screens. "Profile"
 * is intentionally inert here — logout/profile actions already live in
 * ScreenHeader's profile menu, and there's no separate Profile screen yet,
 * so this tab is visual-only until one exists (kept rather than removed,
 * to match the reference's four-tab layout).
 */
export function BottomNavBar({ active, onNavigateHome, onNavigateRequests }: BottomNavBarProps) {
  const handlePress = (key: NavKey) => {
    if (key === 'home') onNavigateHome();
    if (key === 'requests') onNavigateRequests();
    // 'book' is the current screen; 'profile' has no destination yet.
  };

  return (
    <View style={styles.bar}>
      {ITEMS.map((item) => {
        const isActive = item.key === active;
        return (
          <Pressable key={item.key} style={styles.item} onPress={() => handlePress(item.key)}>
            <Ionicons name={item.icon} size={20} color={isActive ? colors.blue : colors.textMuted} />
            <Text style={[styles.label, isActive && styles.labelActive]}>{item.label}</Text>
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  bar: {
    flexDirection: 'row',
    borderTopWidth: 1,
    borderTopColor: colors.border,
    backgroundColor: colors.white,
    paddingTop: spacing.sm,
    paddingBottom: spacing.sm,
  },
  item: {
    flex: 1,
    alignItems: 'center',
    gap: 2,
  },
  label: {
    fontSize: 11,
    color: colors.textMuted,
    fontWeight: '600',
  },
  labelActive: {
    color: colors.blue,
  },
});
