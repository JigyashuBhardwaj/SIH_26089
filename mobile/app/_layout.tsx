import { Stack } from 'expo-router';
import { AuthProvider } from '../features/auth';
import { RequestsProvider } from '../features/requests';

/**
 * Root layout for the single mobile app. It only declares the three
 * top-level route groups and provides auth + local request state to all
 * of them.
 */
export default function RootLayout() {
  return (
    <AuthProvider>
      <RequestsProvider>
        <Stack screenOptions={{ headerShown: false }}>
          <Stack.Screen name="index" />
          <Stack.Screen name="role-selection" />
          <Stack.Screen name="(auth)" />
          <Stack.Screen name="(user)" />
          <Stack.Screen name="(worker)" />
        </Stack>
      </RequestsProvider>
    </AuthProvider>
  );
}
