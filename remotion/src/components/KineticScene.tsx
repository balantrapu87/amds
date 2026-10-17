import React, { useLayoutEffect, useMemo, useRef } from 'react';
import { useCurrentFrame, useVideoConfig } from 'remotion';
import gsap from 'gsap';
import * as LucideIcons from 'lucide-react';
import { SceneNode, ThemeTokens } from '../types';

interface KineticSceneProps {
  scene: SceneNode;
  theme: ThemeTokens;
}

/**
 * Robust Dynamic Lucide Icon Resolver.
 * Resolves kebab-case (e.g. 'activity-square') or camelCase / PascalCase names.
 */
const DynamicIcon: React.FC<{
  name: string;
  size?: number;
  color?: string;
  strokeWidth?: number;
}> = ({ name, size = 48, color = '#FFFFFF', strokeWidth = 2 }) => {
  const IconComponent = useMemo(() => {
    // Convert kebab-case or lowercase to PascalCase: 'zap' -> 'Zap', 'cpu' -> 'Cpu'
    const pascalName = name
      .split(/[-_]/)
      .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
      .join('');

    const iconMap = LucideIcons as unknown as Record<string, React.ComponentType<{
      size?: number;
      color?: string;
      strokeWidth?: number;
      className?: string;
    }>>;

    return iconMap[pascalName] || iconMap[`${pascalName}Icon`] || LucideIcons.Sparkles;
  }, [name]);

  return <IconComponent size={size} color={color} strokeWidth={strokeWidth} />;
};

export const KineticScene: React.FC<KineticSceneProps> = ({ scene, theme }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const containerRef = useRef<HTMLDivElement>(null);
  const badgeRef = useRef<HTMLDivElement>(null);
  const titleRef = useRef<HTMLHeadingElement>(null);
  const subtitleRef = useRef<HTMLParagraphElement>(null);
  const bodyRef = useRef<HTMLParagraphElement>(null);
  const cardRef = useRef<HTMLDivElement>(null);
  const timelineRef = useRef<gsap.core.Timeline | null>(null);

  // Initialize paused GSAP timeline once on mount
  useLayoutEffect(() => {
    const ctx = gsap.context(() => {
      const tl = gsap.timeline({ paused: true });

      // Entrance animation sequence
      if (cardRef.current) {
        tl.fromTo(
          cardRef.current,
          { opacity: 0, scale: 0.92, y: 40 },
          { opacity: 1, scale: 1, y: 0, duration: 0.6, ease: 'power3.out' },
          0
        );
      }

      if (badgeRef.current) {
        tl.fromTo(
          badgeRef.current,
          { opacity: 0, scale: 0.5, rotation: -15 },
          { opacity: 1, scale: 1, rotation: 0, duration: 0.5, ease: 'back.out(1.7)' },
          0.1
        );
      }

      if (titleRef.current) {
        tl.fromTo(
          titleRef.current,
          { opacity: 0, y: 30, filter: 'blur(8px)' },
          { opacity: 1, y: 0, filter: 'blur(0px)', duration: 0.7, ease: 'power4.out' },
          0.2
        );
      }

      if (subtitleRef.current) {
        tl.fromTo(
          subtitleRef.current,
          { opacity: 0, x: -25 },
          { opacity: 1, x: 0, duration: 0.6, ease: 'power2.out' },
          0.35
        );
      }

      if (bodyRef.current) {
        tl.fromTo(
          bodyRef.current,
          { opacity: 0, y: 20 },
          { opacity: 1, y: 0, duration: 0.6, ease: 'power2.out' },
          0.45
        );
      }

      timelineRef.current = tl;
    }, containerRef);

    return () => ctx.revert();
  }, []);

  // Drive GSAP timeline purely by Remotion frame ticks
  // Absolute frame determinism: seek(frame / fps)
  useLayoutEffect(() => {
    if (timelineRef.current) {
      const timeInSeconds = frame / fps;
      timelineRef.current.seek(timeInSeconds, false);
    }
  }, [frame, fps]);

  return (
    <div
      ref={containerRef}
      style={{
        width: '100%',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        padding: `${theme.padding * 1.5}px`,
        boxSizing: 'border-box',
        zIndex: 10,
        position: 'relative',
      }}
    >
      <div
        ref={cardRef}
        style={{
          width: '100%',
          maxWidth: '880px',
          backgroundColor: `${theme.surface_color}CC`,
          backdropFilter: 'blur(20px)',
          WebkitBackdropFilter: 'blur(20px)',
          borderRadius: `${theme.border_radius * 1.5}px`,
          border: `1px solid ${theme.primary_color}40`,
          boxShadow: `0 20px 50px -10px ${theme.background_color}E6, 0 0 40px -10px ${theme.primary_color}33`,
          padding: `${theme.padding * 1.5}px`,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          textAlign: 'center',
          boxSizing: 'border-box',
        }}
      >
        {/* Dynamic Icon Badge */}
        <div
          ref={badgeRef}
          style={{
            width: '96px',
            height: '96px',
            borderRadius: `${theme.border_radius}px`,
            background: `linear-gradient(135deg, ${theme.primary_color}, ${theme.secondary_color})`,
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            boxShadow: `0 10px 25px -5px ${theme.primary_color}80`,
            marginBottom: '28px',
          }}
        >
          <DynamicIcon name={scene.icon_asset} size={52} color={theme.text_color} strokeWidth={2.2} />
        </div>

        {/* Title */}
        <h1
          ref={titleRef}
          style={{
            margin: '0 0 16px 0',
            fontFamily: theme.font_family,
            fontSize: '56px',
            fontWeight: 800,
            lineHeight: 1.15,
            color: theme.text_color,
            letterSpacing: '-0.02em',
            textShadow: `0 4px 20px ${theme.background_color}`,
          }}
        >
          {scene.title}
        </h1>

        {/* Subtitle */}
        {scene.subtitle && (
          <p
            ref={subtitleRef}
            style={{
              margin: '0 0 20px 0',
              fontFamily: theme.font_family,
              fontSize: '28px',
              fontWeight: 600,
              lineHeight: 1.35,
              color: theme.accent_color,
            }}
          >
            {scene.subtitle}
          </p>
        )}

        {/* Body Text */}
        {scene.body_text && (
          <p
            ref={bodyRef}
            style={{
              margin: 0,
              fontFamily: theme.font_family,
              fontSize: '22px',
              fontWeight: 400,
              lineHeight: 1.5,
              color: theme.text_muted_color,
              maxWidth: '720px',
            }}
          >
            {scene.body_text}
          </p>
        )}
      </div>
    </div>
  );
};
