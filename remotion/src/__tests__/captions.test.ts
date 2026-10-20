import { describe, it, expect } from 'vitest';
import {
  getActiveWordIndex,
  getCaptionWindow,
  msToFrame,
} from '../utils/captions';
import type { CaptionWord } from '../utils/captions';

const WORDS: CaptionWord[] = [
  { text: 'Welcome', start_ms: 100, end_ms: 450 },
  { text: 'to', start_ms: 450, end_ms: 550 },
  { text: 'the', start_ms: 550, end_ms: 650 },
  { text: 'final', start_ms: 650, end_ms: 900 },
  { text: 'over.', start_ms: 900, end_ms: 1400 },
];

describe('Karaoke caption math', () => {
  it('finds the active word by millisecond position', () => {
    expect(getActiveWordIndex(WORDS, 50)).toBe(-1);      // before first word
    expect(getActiveWordIndex(WORDS, 100)).toBe(0);      // exactly at start
    expect(getActiveWordIndex(WORDS, 300)).toBe(0);      // inside first word
    expect(getActiveWordIndex(WORDS, 500)).toBe(1);      // boundary belongs to the new word
    expect(getActiveWordIndex(WORDS, 1200)).toBe(4);
    expect(getActiveWordIndex(WORDS, 5000)).toBe(-1);    // after the last word
  });

  it('returns a rolling window of up to 5 words centered on the active word', () => {
    const none = getCaptionWindow(WORDS, -1, 5);
    expect(none.start).toBe(0);
    expect(none.end).toBe(5);                            // no active word: show the whole list

    expect(getCaptionWindow(WORDS, 0, 5)).toEqual({ start: 0, end: 5 });
    expect(getCaptionWindow(WORDS, 2, 5)).toEqual({ start: 0, end: 5 }); // centered, clamped left
    expect(getCaptionWindow(WORDS, 4, 5)).toEqual({ start: 2, end: 5 }); // clamped right

    expect(getCaptionWindow(WORDS, 3, 3)).toEqual({ start: 2, end: 5 }); // smaller window
  });

  it('converts milliseconds to frames deterministically', () => {
    expect(msToFrame(0, 30)).toBe(0);
    expect(msToFrame(33, 30)).toBe(1);                   // 33ms @30fps -> frame 1 (round)
    expect(msToFrame(1000, 30)).toBe(30);
    expect(msToFrame(999, 30)).toBe(30);                 // 999ms -> 29.97 -> 30
  });
});
