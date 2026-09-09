import { Ionicons } from '@expo/vector-icons';
import { useState } from 'react';
import { Modal, Pressable, StyleSheet, Text, View } from 'react-native';
import { colors, radius, spacing } from '../constants/theme';

interface ProfileMenuProps {
  name: string;
  roleLabel: string;
  onLogout: () => void;
}

/**
 * The profile/person icon in the top-right corner of a home screen. Tapping
 * it opens a small menu; Logout lives here rather than as a home-screen
 * feature card, per the approved design.
 */
export function ProfileMenu({ name, roleLabel, onLogout }: ProfileMenuProps) {
  const [open, setOpen] = useState(false);

  return (
    <>
      <Pressable
        style={styles.trigger}
        onPress={() => setOpen(true)}
        accessibilityLabel="Profile menu"
        accessibilityRole="button"
      >
        <Ionicons name="person-circle-outline" size={34} color={colors.navy} />
      </Pressable>

      <Modal visible={open} transparent animationType="fade" onRequestClose={() => setOpen(false)}>
        <Pressable style={styles.backdrop} onPress={() => setOpen(false)}>
          <View style={styles.menu}>
            <View style={styles.menuHeader}>
              <Text style={styles.menuName}>{name}</Text>
              <Text style={styles.menuRole}>{roleLabel}</Text>
            </View>
            <Pressable
              style={styles.menuItem}
              onPress={() => {
                setOpen(false);
                onLogout();
              }}
            >
              <Ionicons name="log-out-outline" size={18} color={colors.danger} />
              <Text style={styles.menuItemText}>Logout</Text>
            </Pressable>
          </View>
        </Pressable>
      </Modal>
    </>
  );
}

const styles = StyleSheet.create({
  trigger: {
    padding: spacing.xs,
  },
  backdrop: {
    flex: 1,
    backgroundColor: 'rgba(22, 48, 92, 0.25)',
  },
  menu: {
    position: 'absolute',
    top: 64,
    right: spacing.lg,
    width: 190,
    backgroundColor: colors.white,
    borderRadius: radius.md,
    paddingVertical: spacing.sm,
    shadowColor: '#000',
    shadowOpacity: 0.15,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 4 },
    elevation: 6,
  },
  menuHeader: {
    paddingHorizontal: spacing.md,
    paddingBottom: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
    marginBottom: spacing.xs,
  },
  menuName: {
    fontSize: 14,
    fontWeight: '700',
    color: colors.navy,
  },
  menuRole: {
    fontSize: 12,
    color: colors.textMuted,
  },
  menuItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
  },
  menuItemText: {
    fontSize: 14,
    fontWeight: '600',
    color: colors.danger,
  },
});
