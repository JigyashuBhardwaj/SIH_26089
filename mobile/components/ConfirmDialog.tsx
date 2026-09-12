import { Modal, Pressable, StyleSheet, Text, View } from 'react-native';
import { colors, radius, spacing } from '../constants/theme';

interface ConfirmDialogProps {
  visible: boolean;
  title: string;
  message: string;
  confirmLabel: string;
  cancelLabel: string;
  /** Styles the confirm button as a destructive action (e.g. cancelling a request). */
  destructive?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

/**
 * A generic "are you sure?" modal with two real actions. This is
 * deliberately separate from `ComingSoonDialog`, which only ever has one
 * dismiss action — reusable anywhere the app needs a real yes/no
 * confirmation, starting with Cancel Request.
 */
export function ConfirmDialog({
  visible,
  title,
  message,
  confirmLabel,
  cancelLabel,
  destructive = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={onCancel}>
      <Pressable style={styles.backdrop} onPress={onCancel}>
        <Pressable style={styles.card} onPress={(event) => event.stopPropagation()}>
          <Text style={styles.title}>{title}</Text>
          <Text style={styles.message}>{message}</Text>

          <Pressable
            style={[styles.button, destructive ? styles.destructiveButton : styles.primaryButton]}
            onPress={onConfirm}
          >
            <Text style={destructive ? styles.destructiveButtonText : styles.primaryButtonText}>
              {confirmLabel}
            </Text>
          </Pressable>

          <Pressable style={styles.secondaryButton} onPress={onCancel}>
            <Text style={styles.secondaryButtonText}>{cancelLabel}</Text>
          </Pressable>
        </Pressable>
      </Pressable>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    backgroundColor: 'rgba(16, 42, 92, 0.45)',
    alignItems: 'center',
    justifyContent: 'center',
    padding: spacing.lg,
  },
  card: {
    width: '100%',
    maxWidth: 340,
    backgroundColor: colors.white,
    borderRadius: radius.lg,
    padding: spacing.lg,
  },
  title: {
    fontSize: 18,
    fontWeight: '800',
    color: colors.navy,
    marginBottom: spacing.sm,
    textAlign: 'center',
  },
  message: {
    fontSize: 14,
    color: colors.textSecondary,
    textAlign: 'center',
    marginBottom: spacing.lg,
  },
  button: {
    paddingVertical: 12,
    borderRadius: radius.pill,
    alignItems: 'center',
    marginBottom: spacing.sm,
  },
  primaryButton: {
    backgroundColor: colors.blue,
  },
  primaryButtonText: {
    color: colors.white,
    fontWeight: '700',
  },
  destructiveButton: {
    backgroundColor: colors.error,
  },
  destructiveButtonText: {
    color: colors.white,
    fontWeight: '700',
  },
  secondaryButton: {
    paddingVertical: 12,
    alignItems: 'center',
  },
  secondaryButtonText: {
    color: colors.textSecondary,
    fontWeight: '700',
  },
});
