import React, { useMemo } from 'react';
import {
  AbsoluteFill,
  OffthreadVideo,
  Series,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import { planVideoSequence } from '../utils/video';
import type { VideoSequenceStep } from '../utils/video';
import { KaraokeCaptions } from './KaraokeCaptions';
import type { SceneNode, ThemeTokens } from '../types';

interface VideoSceneProps {
  scene: SceneNode;
  theme: ThemeTokens;
  channelName?: string;
}

/**
 * Full-bleed Wan 2.1 video scene: no card border, edge-to-edge clips,
 * bottom gradient scrim for text legibility, persistent T20CRICTANK brand
 * chip, floating headline and word-level karaoke captions.
 *
 * Gap handling (clips shorter than the scene):
 *  - gap < 1.5s  -> straight cut (last video frame frozen)
 *  - gap >= 1.5s -> Ken-Burns zoom + animated T20CRICTANK wordmark
 */
export const VideoScene: React.FC<VideoSceneProps> = ({ scene, theme, channelName = 'T20CRICTANK' }) => {
  const { fps } = useVideoConfig();
  const clips: string[] = scene.clips || [];

  const durationFrames: number =
    scene.duration_frames || (scene as any).duration_in_frames || 30;

  // Exact per-clip lengths when the engine provided them; equal split otherwise.
  const clipFrames: number[] = useMemo(() => {
    const provided = (scene as any).clip_frames as number[] | undefined;
    if (provided && provided.length === clips.length) return provided;
    const base = Math.floor(durationFrames / Math.max(1, clips.length));
    return clips.map((_, i) => (i === clips.length - 1 ? durationFrames - base * (clips.length - 1) : base));
  }, [clips, durationFrames]);

  const steps: VideoSequenceStep[] = useMemo(
    () => planVideoSequence(durationFrames, clipFrames, fps),
    [durationFrames, clipFrames, fps],
  );

  const lastClip = clips[clips.length - 1];
  const lastClipFrames = clipFrames[clipFrames.length - 1] || 0;
  const accent = theme.accent_color || theme.primary_color || '#06B6D4';
  const textColor = theme.text_color || theme.text_hex || '#F8FAFC';

  return (
    <AbsoluteFill style={{ backgroundColor: '#000000', zIndex: 10 }}>
      {/* Full-bleed clip sequence */}
      <Series>
        {steps.map((step, i) => {
          if (step.type === 'clip') {
            return (
              <Series.Sequence key={`clip-${step.clipIndex}`} durationInFrames={step.durationFrames}>
                <OffthreadVideo
                  src={staticFile(clips[step.clipIndex])}
                  muted
                  style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                />
              </Series.Sequence>
            );
          }
          // Filler: hold the final frame (straight cut) or Ken-Burns + wordmark.
          return (
            <Series.Sequence key={`filler-${i}`} durationInFrames={step.durationFrames}>
              <AbsoluteFill>
                <FillerFrame
                  src={lastClip ? staticFile(lastClip) : ''}
                  startFrom={Math.max(0, lastClipFrames - 1)}
                  mode={step.mode}
                  durationFrames={step.durationFrames}
                />
                {step.mode === 'kenburns' && (
                  <KenBurnsWordmark theme={theme} channelName={channelName} durationFrames={step.durationFrames} />
                )}
              </AbsoluteFill>
            </Series.Sequence>
          );
        })}
      </Series>

      {/* Bottom gradient scrim for legibility */}
      <div
        style={{
          position: 'absolute',
          left: 0,
          right: 0,
          bottom: 0,
          height: '34%',
          background: 'linear-gradient(to top, rgba(0,0,0,0.85) 0%, rgba(0,0,0,0.5) 55%, transparent 100%)',
          pointerEvents: 'none',
          zIndex: 20,
        }}
      />

      {/* Floating headline */}
      {scene.headline && (
        <div
          style={{
            position: 'absolute',
            left: '6%',
            right: '6%',
            bottom: '24%',
            zIndex: 30,
            fontFamily: theme.font_family,
            fontSize: 46,
            fontWeight: 800,
            lineHeight: 1.15,
            letterSpacing: '-0.02em',
            color: textColor,
            textShadow: '0 4px 24px rgba(0,0,0,0.9)',
            pointerEvents: 'none',
          }}
        >
          {scene.headline}
        </div>
      )}

      {/* Word-level karaoke captions */}
      {scene.captions && scene.captions.length > 0 && (
        <KaraokeCaptions
          captions={scene.captions}
          accentColor={accent}
          textColor={textColor}
          surfaceColor={theme.surface_color || '#1E293B'}
          fontFamily={theme.font_family || 'Inter, sans-serif'}
        />
      )}

      {/* Persistent brand chip */}
      <div
        style={{
          position: 'absolute',
          top: '5%',
          left: '5%',
          zIndex: 50,
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          padding: '10px 20px',
          borderRadius: 999,
          backgroundColor: 'rgba(15, 23, 42, 0.65)',
          backdropFilter: 'blur(12px)',
          WebkitBackdropFilter: 'blur(12px)',
          border: `2px solid ${accent}`,
          boxShadow: `0 0 24px ${accent}44`,
          pointerEvents: 'none',
        }}
      >
        <span
          style={{
            width: 10,
            height: 10,
            borderRadius: '50%',
            backgroundColor: accent,
            boxShadow: `0 0 12px ${accent}`,
          }}
        />
        <span
          style={{
            fontFamily: theme.font_family,
            fontSize: 22,
            fontWeight: 800,
            letterSpacing: '0.08em',
            color: textColor,
          }}
        >
          {channelName}
        </span>
      </div>
    </AbsoluteFill>
  );
};