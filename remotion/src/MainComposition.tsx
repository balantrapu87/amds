import React from 'react';
import { Series, AbsoluteFill, Audio, staticFile } from 'remotion';
import { StoryboardContract, SceneNode } from './types/storyboard';
import { GlassBackdrop } from './components/GlassBackdrop';
import { KineticScene } from './components/KineticScene';
import { VideoScene } from './components/VideoScene';
import { TopCaptions } from './components/TopCaptions';
import '@fontsource/inter/400.css';
import '@fontsource/inter/600.css';
import '@fontsource/inter/800.css';

export const MainComposition: React.FC<StoryboardContract> = (props) => {
  const { theme, scenes } = props;
  const channelName = (props as any).channel_name || 'AMDS';

  // Normalize theme tokens (supports both StoryboardContract and legacy models).
  const background = theme.background_hex || (theme as any).background_color || '#0b0f19';
  const primary = theme.primary_hex || (theme as any).primary_color || '#6366F1';
  const secondary = (theme as any).secondary_color || '#8B5CF6';
  const accent = (theme as any).accent_color || '#06B6D4';
  const textColor = theme.text_hex || (theme as any).text_color || '#F8FAFC';
  const surface = (theme as any).surface_color || '#1E293B';
  const muted = (theme as any).text_muted_color || '#94A3B8';
  const fontFamily = theme.font_family || 'Inter, sans-serif';

  const normalizedTheme: any = {
    background_hex: background, primary_hex: primary, text_hex: textColor, font_family: fontFamily,
    background_color: background, primary_color: primary, text_color: textColor,
    secondary_color: secondary, accent_color: accent, surface_color: surface,
    text_muted_color: muted, border_radius: (theme as any).border_radius || 16, padding: (theme as any).padding || 32,
  };

  return (
    <AbsoluteFill style={{ backgroundColor: background, fontFamily, overflow: 'hidden' }}>
      {/* SHARED dark glassmorphism backdrop — identical for every scene. */}
      <GlassBackdrop background={background} primary={primary} secondary={secondary} accent={accent} />

      {/* Persistent brand chip — top-left corner, so the top-center band is reserved
          exclusively for the caption pill. */}
      <div style={{
        position: 'absolute', top: 30, left: 30,
        zIndex: 70, display: 'flex', alignItems: 'center', gap: 10,
        padding: '8px 20px', borderRadius: 999,
        backgroundColor: 'rgba(15, 23, 42, 0.55)',
        backdropFilter: 'blur(12px)', WebkitBackdropFilter: 'blur(12px)',
        border: `1px solid ${accent}55`, boxShadow: `0 0 20px ${accent}33`,
        pointerEvents: 'none',
      }}>
        <span style={{ width: 9, height: 9, borderRadius: '50%', backgroundColor: accent, boxShadow: `0 0 10px ${accent}` }} />
        <span style={{ fontFamily, fontSize: 20, fontWeight: 800, letterSpacing: '0.12em', color: textColor }}>{channelName}</span>
      </div>

      {/* Sequenced Scene Series */}
      <Series>
        {scenes.map((scene: SceneNode) => {
          const sceneId = scene.scene_id || (scene as any).id || 'scene';
          const duration = scene.duration_frames || (scene as any).duration_in_frames || 30;
          const layer = scene.render_layer || (scene as any).layout_type || 'kinetic_typography';
          const headline = scene.headline || (scene as any).title || '';
          const captions = (scene as any).captions;
          // Full-bleed Wan video scenes keep their own (different) treatment.
          const showVideo = Array.isArray((scene as any).clips) && (scene as any).clips.length > 0;

          const normalizedScene: any = {
            ...scene, id: sceneId, scene_id: sceneId,
            duration_in_frames: duration, duration_frames: duration,
            title: headline, headline, icon_asset: scene.icon_asset || 'Zap',
            layout_type: layer, render_layer: layer,
          };

          return (
            <Series.Sequence key={sceneId} durationInFrames={duration} name={sceneId}>
              <AbsoluteFill>
                {/* Embedded per-scene narration (local edge-tts). */}
                {normalizedScene.audio_file && (
                  <Audio src={staticFile(`audio/${normalizedScene.audio_file}`)} />
                )}

                {/* 2D kinetic-typography scene (smart icon + copy). No 3D geometry. */}
                {!showVideo && <KineticScene scene={normalizedScene} theme={normalizedTheme} />}

                {/* Full-bleed Wan video layer (keeps its own background + captions). */}
                {showVideo && (
                  <VideoScene scene={normalizedScene} theme={normalizedTheme} channelName={channelName} />
                )}

                {/* Styled word-level captions, pinned to the TOP, audio-synced. */}
                {!showVideo && captions && captions.length > 0 && (
                  <TopCaptions
                    captions={captions}
                    accentColor={accent}
                    textColor={textColor}
                    surfaceColor={surface}
                    fontFamily={fontFamily}
                  />
                )}
              </AbsoluteFill>
            </Series.Sequence>
          );
        })}
      </Series>
    </AbsoluteFill>
  );
};
