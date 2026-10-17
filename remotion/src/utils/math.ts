/**
 * Deterministic mathematical helpers for Remotion animations.
 * Strictly adheres to the Deterministic Frame Law:
 * State = f(frame, fps) with zero wall-clock timing or unseeded randomness.
 */

/**
 * Calculates deterministic radians for rotational transformations.
 *
 * @param frame - Current frame number (from useCurrentFrame())
 * @param fps - Frames per second (from useVideoConfig())
 * @param speed - Rotational speed in full revolutions per second
 * @returns Angular rotation in radians
 */
export function frameToRadian(frame: number, fps: number, speed: number = 1.0): number {
  if (fps <= 0) {
    throw new Error(`FPS must be greater than 0, received: ${fps}`);
  }
  return (frame / fps) * speed * 2 * Math.PI;
}
