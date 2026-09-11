/**
 * KARMANYA design tokens.
 *
 * Colors are read off the approved reference images (blue = User identity,
 * green = Worker identity, navy for headings, soft tints for card
 * backgrounds). Centralized here so every screen stays visually
 * consistent without hard-coding hex values in each file.
 */

export const colors = {
  // Brand — exact approved palette, do not introduce new hues.
  navy: '#102A5C', // Primary Text
  primaryBlue: '#0B3D91', // Primary Blue (deep accents, logo-adjacent elements)
  blue: '#1565C0', // Action Blue (buttons, links, User accent)
  blueDark: '#0B3D91',
  blueTint: '#EAF5FF', // Light Blue
  blueBorder: '#D9E4F0',

  green: '#2E7D32', // Karmanya Green
  greenDark: '#1B5E20',
  greenTint: '#EAF8EF', // Light Green
  greenBorder: '#D9E4F0',

  // Neutrals
  white: '#FFFFFF',
  background: '#F6F9FC',
  textPrimary: '#102A5C',
  textSecondary: '#64748B', // Secondary Text
  textMuted: '#8A97A8',
  border: '#D9E4F0',
  danger: '#DC2626',

  skyline: '#B9C9DE',
  hardHat: '#FBC02D',

  // Status colors (locked)
  warning: '#F59E0B',
  error: '#D32F2F',
  success: '#2E7D32',
} as const;

export const spacing = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
  xxl: 48,
} as const;

export const radius = {
  sm: 8,
  md: 14,
  lg: 20,
  pill: 999,
} as const;

export const typography = {
  brandTitle: {
    fontSize: 26,
    fontWeight: '800' as const,
    color: colors.navy,
    letterSpacing: 0.5,
  },
  brandTagline: {
    fontSize: 11,
    fontWeight: '600' as const,
    color: colors.textSecondary,
    letterSpacing: 1.2,
    textTransform: 'uppercase' as const,
  },
  heading: {
    fontSize: 24,
    fontWeight: '800' as const,
    color: colors.navy,
  },
  subheading: {
    fontSize: 14,
    fontWeight: '400' as const,
    color: colors.textSecondary,
  },
};
