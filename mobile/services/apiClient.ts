/**
 * Small, generic HTTP client for talking to the real Karmanya backend.
 *
 * Phase 6A foundation: base URL from environment configuration (never
 * hardcoded), a single `request()` helper that attaches a Bearer token
 * when one is supplied, handles JSON in/out, and turns any non-2xx
 * response into a typed `ApiError` — every caller gets consistent error
 * handling instead of reimplementing `fetch`/`response.ok` checks.
 *
 * Deliberately uses the native `fetch` API (available in the Expo/React
 * Native runtime) rather than adding axios, per the locked Phase 6A
 * scope.
 */

/**
 * `EXPO_PUBLIC_*` environment variables are inlined at build time by
 * Expo's bundler (no extra config needed, unlike `expo-constants`
 * `extra`), which is why this reads directly from `process.env` rather
 * than `Constants.expoConfig`.
 */
const API_BASE_URL = process.env.EXPO_PUBLIC_API_BASE_URL;

if (!API_BASE_URL) {
  // Fails loudly at import time rather than producing confusing
  // "Network request failed" errors deep inside a login attempt.
  console.warn(
    'EXPO_PUBLIC_API_BASE_URL is not set. Copy mobile/.env.example to mobile/.env and set it to your backend URL.'
  );
}

/**
 * Thrown for any non-2xx response. `status` lets callers distinguish
 * "invalid credentials" (401) from other failures without string-
 * matching the message. `message` is always a safe, user-facing string
 * — never a raw backend stack trace.
 */
export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

/** Thrown when the backend can't be reached at all (offline, wrong URL, server down). */
export class NetworkUnavailableError extends Error {
  constructor() {
    super('Could not reach the server. Check your connection and try again.');
    this.name = 'NetworkUnavailableError';
  }
}

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  body?: unknown;
  /** Bearer token to attach, if the caller is authenticated. */
  token?: string | null;
}

/**
 * Extracts a safe, user-facing message from a FastAPI-style error body
 * (`{"detail": "..."}` or `{"detail": [{"msg": "..."}]}`) without ever
 * surfacing raw internals if the body doesn't match that shape.
 */
function extractErrorMessage(body: unknown, fallback: string): string {
  if (body && typeof body === 'object' && 'detail' in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === 'string') {
      return detail;
    }
    if (Array.isArray(detail) && detail.length > 0 && typeof detail[0]?.msg === 'string') {
      return detail[0].msg;
    }
  }
  return fallback;
}

/**
 * Performs a JSON request against the backend. Resolves with the parsed
 * JSON body on any 2xx response (or `undefined` for an empty body).
 * Rejects with `ApiError` for a non-2xx response, or
 * `NetworkUnavailableError` if the request never reached the server.
 */
export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  if (!API_BASE_URL) {
    throw new NetworkUnavailableError();
  }

  const headers: Record<string, string> = { Accept: 'application/json' };
  if (options.body !== undefined) {
    headers['Content-Type'] = 'application/json';
  }
  if (options.token) {
    headers.Authorization = `Bearer ${options.token}`;
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method: options.method ?? 'GET',
      headers,
      body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
    });
  } catch {
    // fetch() throws (rather than resolving) when the request can't be
    // sent at all — DNS failure, connection refused, offline, etc.
    throw new NetworkUnavailableError();
  }

  const contentType = response.headers.get('content-type') ?? '';
  const responseBody = contentType.includes('application/json') ? await response.json().catch(() => undefined) : undefined;

  if (!response.ok) {
    throw new ApiError(response.status, extractErrorMessage(responseBody, 'Something went wrong. Please try again.'));
  }

  return responseBody as T;
}
