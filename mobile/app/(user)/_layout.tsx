import { Stack } from 'expo-router';

/**
 * Layout for the User flow route group. Home, booking creation, ongoing
 * requests, etc. are built in Phase 3 (User App).
 */
export default function UserLayout() {
  return <Stack screenOptions={{ headerShown: false }} />;
}
