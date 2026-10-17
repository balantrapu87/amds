import { describe, it, expect } from 'vitest';
import { frameToRadian } from '../utils/math';

describe('Deterministic Frame Math — frameToRadian', () => {
  it('calculates deterministic radians at frames 0, 15, and 30 for 30fps and 1.0 speed', () => {
    const fps = 30;
    const speed = 1.0;

    // Frame 0: exactly 0 radians
    expect(frameToRadian(0, fps, speed)).toBe(0);

    // Frame 15: half second = half rotation = Math.PI radians
    expect(frameToRadian(15, fps, speed)).toBeCloseTo(Math.PI, 6);

    // Frame 30: 1 full second = 1 full rotation = 2 * Math.PI radians
    expect(frameToRadian(30, fps, speed)).toBeCloseTo(2 * Math.PI, 6);
  });

  it('scales linearly with speed multiplier', () => {
    const fps = 30;
    const speed = 2.0;

    expect(frameToRadian(0, fps, speed)).toBe(0);
    expect(frameToRadian(15, fps, speed)).toBeCloseTo(2 * Math.PI, 6);
    expect(frameToRadian(30, fps, speed)).toBeCloseTo(4 * Math.PI, 6);
  });
});
