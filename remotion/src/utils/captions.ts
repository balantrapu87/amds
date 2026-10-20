/**
 * Word-level karaoke caption math (Deterministic Frame Law compliant).
 * Pure functions: state = f(frame, fps, captions), no wall-clock timing.
 */

export interface CaptionWord {
  text: string;
  start_ms: number;
  end_ms: number;
}

/**
 * Index of the word spoken at the given scene-relative millisecond,
 * or -1 when no word is active (before the first / after the last).
 * A boundary millisecond belongs to the word that starts there.
 */
export function getActiveWordIndex(words: CaptionWord[], currentMs: number): number {
  for (let i = 0; i < words.length; i += 1) {
    if (currentMs >= words[i].start_ms && currentMs < words[i].end_ms) {
      return i;
    }
  }
  return -1;
}

/**
 * Rolling window of words to display, centered on the active word.
 * Without an active word the whole list is shown. Clamped to [0, words.length].
 */
export function getCaptionWindow(
  words: CaptionWord[],
  activeIndex: number,
  windowSize = 5,
): { start: number; end: number } {
  if (activeIndex < 0) {
    return { start: 0, end: words.length };
  }
  const half = Math.floor(windowSize / 2);
  const start = Math.max(0, activeIndex - half);
  const end = Math.min(words.length, start + windowSize);
  return { start, end };
}

/** Deterministic millisecond -> frame conversion (round half up). */
export function msToFrame(ms: number, fps: number): number {
  if (fps <= 0) {
    throw new Error(`FPS must be greater than 0, received: ${fps}`);
  }
  return Math.round((ms / 1000) * fps);
}
