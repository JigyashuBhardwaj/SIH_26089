import { useCallback, useState } from 'react';

/**
 * Pairs with <ComingSoonDialog />. Any screen with non-functional feature
 * cards calls `show()` on tap and passes `visible`/`dismiss` straight to
 * the dialog — no per-screen dialog state duplication.
 */
export function useComingSoon() {
  const [visible, setVisible] = useState(false);

  const show = useCallback(() => setVisible(true), []);
  const dismiss = useCallback(() => setVisible(false), []);

  return { visible, show, dismiss };
}
