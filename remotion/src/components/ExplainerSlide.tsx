import React, { useMemo } from 'react';
import { AbsoluteFill, useCurrentFrame } from 'remotion';
import * as LucideIcons from 'lucide-react';

export interface ExplainerSlideProps {
  index?: number;
  total?: number;
  icon?: string;
  kicker?: string;
  title?: string;
  body?: string;
  accent?: string;
  primary?: string;
}

type LooseProps = Record<string, unknown> & Partial<ExplainerSlideProps>;

const DynamicIcon: React.FC<{ name: string; size?: number; color?: string; strokeWidth?: number }> = ({
  name, size = 96, color = '#FFFFFF', strokeWidth = 1.8,
}) => {
  const Icon = useMemo(() => {
    const pascal = name.split(/[-_]/).map((s) => s.charAt(0).toUpperCase() + s.slice(1)).join('');
    const map = LucideIcons as unknown as Record<string, React.ComponentType<{ size?: number; color?: string; strokeWidth?: number }>>;
    return map[pascal] || map[`${pascal}Icon`] || LucideIcons.Sparkles;
  }, [name]);
  return <Icon size={size} color={color} strokeWidth={strokeWidth} />;
};

/**
 * Dark glassmorphism explainer slide. 1080x1350 (4:5) social-post canvas.
 * Deterministic: the only animation is a subtle frame-driven glow drift.
 */
export const ExplainerSlide: React.FC<LooseProps> = ({
  index = 0, total = 5, icon = 'zap', kicker = 'Step 01', title = 'Slide Title', body = 'Explanatory copy.',
  accent = '#06B6D4', primary = '#6366F1',
}) => {
  const frame = useCurrentFrame();
  // Gentle deterministic drift of the ambient orbs (frame-based, not wall clock).
  const drift = (frame / 30) * 10; // ~10px/s

  return (
    <AbsoluteFill
      style={{
        backgroundColor: '#070A14',
        fontFamily: 'Inter, sans-serif',
        overflow: 'hidden',
      }}
    >
      {/* Ambient orbs (drift slowly with frame) */}
      <div style={{
        position: 'absolute', top: -180 + drift, left: -160, width: 620, height: 620, borderRadius: '50%',
        background: `radial-gradient(circle, ${primary}55 0%, transparent 70%)`, filter: 'blur(20px)',
      }} />
      <div style={{
        position: 'absolute', bottom: -220 - drift, right: -140, width: 560, height: 560, borderRadius: '50%',
        background: `radial-gradient(circle, ${accent}44 0%, transparent 70%)`, filter: 'blur(20px)',
      }} />

      {/* Faint grid */}
      <div style={{
        position: 'absolute', inset: 0, opacity: 0.06,
        backgroundImage: 'linear-gradient(#38bdf8 1px, transparent 1px), linear-gradient(90deg, #38bdf8 1px, transparent 1px)',
        backgroundSize: '54px 54px',
      }} />

      {/* Glass panel */}
      <div style={{
        position: 'absolute', top: '7%', left: '6%', right: '6%', bottom: '7%',
        borderRadius: 48,
        background: 'rgba(17, 24, 39, 0.55)',
        backdropFilter: 'blur(28px)', WebkitBackdropFilter: 'blur(28px)',
        border: '1px solid rgba(148, 163, 184, 0.18)',
        boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.06), 0 40px 90px -30px rgba(0,0,0,0.7)',
        overflow: 'hidden',
      }}>
        {/* progress rail */}
        <div style={{ position: 'absolute', top: 40, left: 48, right: 48, height: 6, borderRadius: 3, background: 'rgba(148,163,184,0.15)' }}>
          <div style={{
            height: '100%', borderRadius: 3,
            width: `${((index + 1) / total) * 100}%`,
            background: `linear-gradient(90deg, ${primary}, ${accent})`,
          }} />
        </div>

        <div style={{
          position: 'absolute', top: 92, left: 56, right: 56,
          display: 'flex', flexDirection: 'column', alignItems: 'flex-start',
        }}>
          {/* icon medallion */}
          <div style={{
            width: 148, height: 148, borderRadius: 36,
            background: `linear-gradient(135deg, ${primary}, ${accent})`,
            display: 'flex', justifyContent: 'center', alignItems: 'center',
            boxShadow: `0 24px 60px -18px ${primary}AA, 0 0 0 1px rgba(255,255,255,0.08) inset`,
            marginBottom: 44,
          }}>
            <DynamicIcon name={icon} size={84} color="#F8FAFC" strokeWidth={1.6} />
          </div>

          <div style={{
            fontFamily: 'Inter, sans-serif', fontSize: 24, fontWeight: 700, letterSpacing: '0.28em',
            textTransform: 'uppercase', color: accent, marginBottom: 18,
          }}>
            {kicker}
          </div>

          <h1 style={{
            margin: 0, fontFamily: 'Inter, sans-serif', fontSize: 78, fontWeight: 800, lineHeight: 1.08,
            letterSpacing: '-0.02em', color: '#F8FAFC',
          }}>
            {title}
          </h1>

          <div style={{
            marginTop: 34, width: 120, height: 6, borderRadius: 3,
            background: `linear-gradient(90deg, ${primary}, ${accent})`,
          }} />

          <p style={{
            margin: '36px 0 0 0', fontFamily: 'Inter, sans-serif', fontSize: 34, fontWeight: 400,
            lineHeight: 1.55, color: '#CBD5E1', maxWidth: 820,
          }}>
            {body}
          </p>
        </div>

        {/* footer caption */}
        <div style={{
          position: 'absolute', left: 56, right: 56, bottom: 44,
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          fontFamily: 'Inter, sans-serif', fontSize: 22, fontWeight: 600, color: '#64748B',
          letterSpacing: '0.12em',
        }}>
          <span>AMDS · Autonomous Motion Design Studio</span>
          <span>{String(index + 1).padStart(2, '0')} / {String(total).padStart(2, '0')}</span>
        </div>
      </div>
    </AbsoluteFill>
  );
};
