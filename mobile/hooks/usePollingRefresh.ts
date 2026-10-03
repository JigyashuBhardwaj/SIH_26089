import { useFocusEffect } from 'expo-router';
import { useCallback, useRef } from 'react';

/** `usePollingRefresh`'s default interval between poll ticks, in milliseconds. */
const DEFAULT_INTERVAL_MS = 5000;

interface UsePollingRefreshOptions {
  /**
   * Called on each poll tick. This should be the screen's own existing
   * reload function (or a thin wrapper around it) — `usePollingRefresh`
   * never fetches anything itself, it only decides when to call this.
   */
  onPoll: () => Promise<void>;
  /**
   * While `true`, poll ticks are skipped entirely — e.g. while the
   * screen's own mutation (cancel/accept/decline/etc.) is in flight, so a
   * background poll can never race it.
   */
  isPaused?: boolean;
  /** Milliseconds between poll ticks. Defaults to `DEFAULT_INTERVAL_MS` (5000). */
  intervalMs?: number;
}

/**
 * Phase 6G: focus-aware background polling for a single screen, reusing
 * that screen's own existing reload function — this hook never performs
 * a fetch of its own.
 *
 * - Starts only while the screen is focused (`expo-router`'s
 *   `useFocusEffect`) and is torn down on blur/unmount, so a backgrounded
 *   or navigated-away screen never keeps polling in the background.
 * - A tick is skipped (not queued) if the previous tick is still in
 *   flight — a slow response can never cause overlapping requests — or if
 *   `isPaused` is `true`. Either way the next scheduled tick still fires
 *   on time; nothing is retried early.
 * - `onPoll` rejections are swallowed here. This is a background refresh,
 *   not a user-initiated action, so a poll failure must never replace the
 *   screen with its own full error state — if `onPoll` is a "silent"
 *   variant of the screen's reload (see call sites), it doesn't touch
 *   that error state itself either; if it's the plain reload, its own
 *   existing error handling runs as normal, but a *network*-level
 *   rejection that reaches here is still swallowed rather than thrown
 *   into an unhandled rejection.
 */
export function usePollingRefresh({ onPoll, isPaused = false, intervalMs = DEFAULT_INTERVAL_MS }: UsePollingRefreshOptions): void {
  // Read the latest onPoll/isPaused from inside the interval without
  // needing to recreate it every render.
  const onPollRef = useRef(onPoll);
  onPollRef.current = onPoll;
  const isPausedRef = useRef(isPaused);
  isPausedRef.current = isPaused;

  // Guards a single in-flight tick so a slow response can never overlap
  // with the next scheduled one.
  const isTickInFlightRef = useRef(false);

  useFocusEffect(
    useCallback(() => {
      const intervalId = setInterval(() => {
        if (isPausedRef.current || isTickInFlightRef.current) {
          return;
        }
        isTickInFlightRef.current = true;
        // `onPoll` is expected to return a Promise (its declared contract),
        // but a caller could still throw synchronously before returning
        // one (a bug in the reload function it wraps, say). Without this
        // try/catch, that synchronous throw would skip the
        // `.catch()/.finally()` below entirely and leave
        // `isTickInFlightRef.current` stuck `true` forever, silently
        // disabling all future ticks. Resolving to a rejected promise
        // routes both failure modes through the same `.catch()/.finally()`
        // cleanup below.
        let tick: Promise<void>;
        try {
          tick = onPollRef.current();
        } catch (err) {
          tick = Promise.reject(err);
        }
        tick
          .catch(() => {
            // Silent by design — see the hook's doc comment above.
          })
          .finally(() => {
            isTickInFlightRef.current = false;
          });
      }, intervalMs);

      return () => clearInterval(intervalId);
    }, [intervalMs])
  );
}
