import React from 'react';
import { AbsoluteFill, useCurrentFrame } from 'remotion';

interface GlassBackdropProps {
  background: string;
  primary: string;
  secondary: string;
  accent: string;
}

/**
 * Dark glassmorphism backdrop shared by EVERY scene (the "same background"
 * requirement). No 3D geometry — instead a deep slate field, two slowly
 * drifting colour orbs, a faint grid, and a glass sheen. The drift is a pure
 * function of the frame, so it stays deterministic across the whole video.
 */
export const GlassBackdrop: React.FC<GlassBackdropProps> = ({ background, primary, secondary, accent }) => {
  const frame = useCurrentFrame();
  const drift = (frame / 30) * 6; // ~6px/s, gentle

  return (
    <AbsoluteFill style={{ backgroundColor: background, overflow: 'hidden' }}>
      {/* top-left primary orb */}
      <div style={{
        position: 'absolute', top: -260 + drift, left: -200, width: 900, height: 900,
        borderRadius: '50%',
        background: `radial-gradient(circle, ${primary}40 0%, transparent 68%)`,
        filter: 'blur(30px)',
      }} />
      {/* bottom-right accent orb */}
      <div style={{
        position: 'absolute', bottom: -300 - drift, right: -220, width: 820, height: 820,
        borderRadius: '50%',
        background: `radial-gradient(circle, ${accent}33 0%, transparent 68%)`,
        filter: 'blur(30px)',
      }} />
      {/* mid secondary orb */}
      <div style={{
        position: 'absolute', top: '30%', left: '55%', width: 560, height: 560,
        borderRadius: '50%',
        background: `radial-gradient(circle, ${secondary}2e 0%, transparent 70%)`,
        filter: 'blur(40px)',
      }} />

      {/* faint grid */}
      <div style={{
        position: 'absolute', inset: 0, opacity: 0.05,
        backgroundImage: `linear-gradient(${primary} 1px, transparent 1px), linear-gradient(90deg, ${primary} 1px, transparent 1px)`,
        backgroundSize: '64px 64px',
      }} />

      {/* glass sheen sweep (very subtle, frame-driven) */}
      <div style={{
        position: 'absolute', top: 0, left: 0, right: 0, height: '38%',
        background: 'linear-gradient(to bottom, rgba(255,255,255,0.05), transparent)',
        transform: `translateY(${drift * 0.3}px)`,
      }} />
    </AbsoluteFill>
  );
};
