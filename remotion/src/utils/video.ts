/**
 * Full-bleed video scene sequencing (Deterministic Frame Law compliant).
 *
 * Clips are generated to cover (or slightly overshoot) the scene duration.
 * - Overshoot: the final clip is trimmed to fit the scene exactly.
 * - Undershoot (gap):
 *   - gap <  FILLER_THRESHOLD_FRAMES (1.5s @ 30fps) -> 'cut' (freeze last frame)
 *   - gap >= FILLER_THRESHOLD_FRAMES                -> 'kenburns' (slow zoom +
 *     animated T20CRICTANK wordmark over the final clip)
 */

export type VideoSequenceStep =
  | { type: 'clip'; clipIndex: number; durationFrames: number }
  | { type: 'filler'; mode: 'cut' | 'kenburns'; durationFrames: number };

/** 1.5 seconds at 30fps — below this gap a straight cut is preferred. */
export const FILLER_THRESHOLD_FRAMES = 45;

export function planVideoSequence(
  durationFrames: number,
  clipFrames: number[],
  fps: number,
): VideoSequenceStep[] {
  if (fps <= 0) {
    throw new Error(`FPS must be greater than 0, received: ${fps}`);
  }
  const steps: VideoSequenceStep[] = [];
  let consumed = 0;

  for (let i = 0; i < clipFrames.length; i += 1) {
    const remaining = durationFrames - consumed;
    if (remaining <= 0) break;
    const clipDuration = Math.min(clipFrames[i], remaining);
    if (clipDuration <= 0) break;
    steps.push({ type: 'clip', clipIndex: i, durationFrames: clipDuration });
    consumed += clipDuration;
  }

  const gap = durationFrames - consumed;
  if (gap > 0) {
    steps.push({
      type: 'filler',
      mode: gap >= FILLER_THRESHOLD_FRAMES ? 'kenburns' : 'cut',
      durationFrames: gap,
    });
  }
  return steps;
}
