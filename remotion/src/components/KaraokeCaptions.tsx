import React from 'react';
import { useCurrentFrame, useVideoConfig } from 'remotion';
import { getActiveWordIndex, getCaptionWindow } from '../utils/captions';
import type { CaptionWord } from '../utils/captions';

interface KaraokeCaptionsProps {
  captions: CaptionWord[];
  accentColor: string;
  textColor: string;
  surfaceColor: string;
  fontFamily: string;
}

/**
 * Word-level karaoke captions: a rolling window of ~5 words where the word
 * currently being spoken is highlighted in the accent color and pops.
 * Purely frame-driven (Deterministic Frame Law): no GSAP, no wall clock.
 */
export const KaraokeCaptions: React.FC<KaraokeCaptionsProps> = ({
  captions,
  accentColor,
  textColor,
  surfaceColor,
  fontFamily,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  if (!captions || captions.length === 0) {
    return null;
  }

  const currentMs = (frame * 1000) / fps;
  const activeIndex = getActiveWordIndex(captions, currentMs);
  const { start, end } = getCaptionWindow(captions, activeIndex, 5);
  const visible = captions.slice(start, end);

  return (
    <div
      style={{
        position: 'absolute',
        bottom: '18%',
        left: 0,
        right: 0,
        display: 'flex',
        justifyContent: 'center',
        gap: '12px',
        pointerEvents: 'none',
        zIndex: 40,
      }}
    >
      {visible.map((word, i) => {
        const index = start + i;
        const isActive = index === activeIndex;
        // Deterministic pop: active word scales 1.12 -> 1.0 over its lifetime.
        const progress = isActive
          ? Math.min(1, Math.max(0, (currentMs - word.start_ms) / Math.max(1, word.end_ms - word.start_ms)))
          : 0;
        const scale = isActive ? 1.12 - 0.12 * progress : 1;
        return (
          <span
            key={index}
            style={{
              display: 'inline-block',
              padding: '6px 14px',
              borderRadius: 999,
              fontFamily,
              fontSize: 34,
              fontWeight: 800,
              letterSpacing: '-0.01em',
              backgroundColor: isActive ? `${accentColor}33` : `${surfaceColor}B3`,
              border: `1px solid ${isActive ? accentColor : 'transparent'}`,
              color: isActive ? accentColor : textColor,
              opacity: isActive || activeIndex === -1 ? 1 : 0.45,
              transform: `scale(${scale})`,
              transition: 'none', // frames are deterministic; no CSS timing
              boxShadow: isActive ? `0 0 24px ${accentColor}66` : 'none',
            }}
          >
            {word.text}
          </span>
        );
      })}
    </div>
  );
};