/**
 * A tiny seeded PRNG (mulberry32) used only to build the static synthetic
 * worker dataset in `workerCatalog.ts`. This is NOT `Math.random()` — the
 * same seed always produces the exact same sequence, on every run, every
 * reload, every build. That's what makes the generated dataset
 * effectively static: it's computed once from fixed inputs, not
 * regenerated differently each time the app runs.
 */
export function createSeededRandom(seed: number): () => number {
  let state = seed >>> 0;
  return function random() {
    state |= 0;
    state = (state + 0x6d2b79f5) | 0;
    let t = Math.imul(state ^ (state >>> 15), 1 | state);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** Picks a deterministic element from an array using the given random() function. */
export function pick<T>(random: () => number, items: readonly T[]): T {
  return items[Math.floor(random() * items.length)];
}

/** Deterministic integer in [min, max], inclusive. */
export function intBetween(random: () => number, min: number, max: number): number {
  return min + Math.floor(random() * (max - min + 1));
}
