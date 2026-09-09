import { Stack } from 'expo-router';

/**
 * Layout for the auth route group. Actual login/signup/forgot-password
 * screens are built in Phase 2.
 */
export default function AuthLayout() {
  return <Stack screenOptions={{ headerShown: false }} />;
}
