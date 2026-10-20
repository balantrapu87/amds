import { describe, it, expect } from 'vitest';
import { planVideoSequence, FILLER_THRESHOLD_FRAMES } from '../utils/video';

describe('Full-bleed video scene sequencing', () => {
  it('trims the final clip when clips overshoot the scene duration', () => {
    // scene is 150f, clips are 81+81 = 162f -> second clip trimmed to 69f
    const seq = planVideoSequence(150, [81, 81], 30);
    expect(seq).toHaveLength(2);
    expect(seq[0]).toEqual({ type: 'clip', clipIndex: 0, durationFrames: 81 });
    expect(seq[1]).toEqual({ type: 'clip', clipIndex: 1, durationFrames: 69 });
    expect(seq.some((s) => s.type === 'filler')).toBe(false);
  });

  it('cuts straight when the gap is below the 1.5s filler threshold', () => {
    // scene 200f, clips 81+81 = 162f -> gap 38f (1.27s) < 45f threshold
    const seq = planVideoSequence(200, [81, 81], 30);
    const filler = seq.find((s) => s.type === 'filler');
    expect(filler).toBeDefined();
    expect((filler as any).mode).toBe('cut');
    expect((filler as any).durationFrames).toBe(38);
  });

  it('uses Ken-Burns wordmark filler when the gap is >= 1.5s', () => {
    // scene 260f, clips 81+81 = 162f -> gap 98f >= 45f threshold
    const seq = planVideoSequence(260, [81, 81], 30);
    const filler = seq.find((s) => s.type === 'filler');
    expect(filler).toBeDefined();
    expect((filler as any).mode).toBe('kenburns');
    expect((filler as any).durationFrames).toBe(98);
  });

  it('exposes the 1.5s @ 30fps threshold constant', () => {
    expect(FILLER_THRESHOLD_FRAMES).toBe(45);
  });

  it('handles a single clip that exactly fills the scene', () => {
    const seq = planVideoSequence(81, [81], 30);
    expect(seq).toEqual([{ type: 'clip', clipIndex: 0, durationFrames: 81 }]);
  });
});
