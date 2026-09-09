import { Stack } from 'expo-router';

/**
 * Layout for the Worker flow route group. Booking requests, accepted
 * requests, etc. are built in Phase 6 (Worker App).
 */
export default function WorkerLayout() {
  return <Stack screenOptions={{ headerShown: false }} />;
}
