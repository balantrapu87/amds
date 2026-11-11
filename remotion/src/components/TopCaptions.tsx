import React from 'react';
import { useCurrentFrame, useVideoConfig } from 'remotion';
import { getActiveWordIndex, getCaptionWindow } from '../utils/captions';
import type { CaptionWord } from '../utils/captions';

interface TopCaptionsProps {
  captions: CaptionWord[];
  accentColor: string;
  textColor: string;
  surfaceColor: string;
  fontFamily: string;
}

/**
 * Word-level captions rendered in the TOP band of the frame (a pill-shaped
 * glass chip). The active word pops in the accent color; the rest dim.
 * Purely frame-driven — deterministic.
 */
export const TopCaptions: React.FC<TopCaptionsProps> = ({
  captions, accentColor, textColor, surfaceColor, fontFamily,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  if (!captions || captions.length === 0) return null;

  const currentMs = (frame * 1000) / fps;
  const activeIndex = getActiveWordIndex(captions, currentMs);
  // No word is being spoken (scene lead-in / tail) -> show nothing.
  if (activeIndex < 0) return null;
  // 4-word window: a short phrase that always fits one line.
  const { start, end } = getCaptionWindow(captions, activeIndex, 4);
  const visible = captions.slice(start, end);

  return (
    <div style={{
      position: 'absolute', top: 46, left: '50%', transform: 'translateX(-50%)',
      zIndex: 60, pointerEvents: 'none',
      display: 'flex', justifyContent: 'center',
    }}>
      {/* Single line, no wrap — never two lines, never wraps mid-word. */}
      <div style={{
        display: 'inline-flex', flexWrap: 'nowrap', alignItems: 'center',
        gap: 4, whiteSpace: 'nowrap', maxWidth: '94%', overflow: 'hidden',
        padding: '12px 28px', borderRadius: 999,
        backgroundColor: `${surfaceColor}B3`,
        backdropFilter: 'blur(16px)', WebkitBackdropFilter: 'blur(16px)',
        border: `1px solid ${accentColor}40`,
        boxShadow: `0 12px 40px -12px rgba(0,0,0,0.6), 0 0 28px -6px ${accentColor}33`,
      }}>
        {visible.map((word, i) => {
          const index = start + i;
          const isActive = index === activeIndex;
          const progress = isActive
            ? Math.min(1, Math.max(0, (currentMs - word.start_ms) / Math.max(1, word.end_ms - word.start_ms)))
            : 0;
          const scale = isActive ? 1.14 - 0.14 * progress : 1;
          return (
            <span key={index} style={{
              display: 'inline-block', padding: '2px 8px',
              fontFamily, fontSize: 27, fontWeight: 800, letterSpacing: '-0.01em',
              color: isActive ? accentColor : textColor,
              opacity: isActive || activeIndex === -1 ? 1 : 0.5,
              transform: `scale(${scale})`,
              textShadow: isActive ? `0 0 22px ${accentColor}AA` : 'none',
              whiteSpace: 'nowrap',
            }}>
              {word.text}{(i < visible.length - 1) ? '\u00A0' : ''}
            </span>
          );
        })}
      </div>
    </div>
  );
};
