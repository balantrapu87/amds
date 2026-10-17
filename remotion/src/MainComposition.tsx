import React from 'react';
import { Series, AbsoluteFill, useVideoConfig } from 'remotion';
import { StoryboardContract, SceneNode } from './types/storyboard';
import { ThreeScene } from './components/ThreeScene';
import { KineticScene } from './components/KineticScene';
import '@fontsource/inter/400.css';
import '@fontsource/inter/600.css';
import '@fontsource/inter/800.css';

export const MainComposition: React.FC<StoryboardContract> = (props) => {
  const { theme, scenes } = props;
  const { width, height } = useVideoConfig();

  // Normalize theme tokens supporting both StoryboardContract and legacy models
  const backgroundColor = theme.background_hex || (theme as any).background_color || '#0b0f19';
  const primaryColor = theme.primary_hex || (theme as any).primary_color || '#38bdf8';
  const textColor = theme.text_hex || (theme as any).text_color || '#f8fafc';
  const fontFamily = theme.font_family || 'Inter, sans-serif';

  const normalizedTheme: any = {
    background_hex: backgroundColor,
    primary_hex: primaryColor,
    text_hex: textColor,
    font_family: fontFamily,
    background_color: backgroundColor,
    primary_color: primaryColor,
    text_color: textColor,
    secondary_color: (theme as any).secondary_color || '#8B5CF6',
    accent_color: (theme as any).accent_color || '#06B6D4',
    surface_color: (theme as any).surface_color || '#1E293B',
    text_muted_color: (theme as any).text_muted_color || '#94A3B8',
    border_radius: (theme as any).border_radius || 16,
    padding: (theme as any).padding || 32,
  };

  return (
    <AbsoluteFill
      style={{
        backgroundColor,
        fontFamily,
        overflow: 'hidden',
      }}
    >
      {/* Dynamic Ambient Background Glow */}
      <div
        style={{
          position: 'absolute',
          top: '-20%',
          left: '-20%',
          width: '140%',
          height: '140%',
          background: `radial-gradient(circle at 50% 40%, ${primaryColor}25 0%, ${normalizedTheme.secondary_color}15 45%, transparent 75%)`,
          pointerEvents: 'none',
        }}
      />

      {/* Sequenced Scene Series */}
      <Series>
        {scenes.map((scene: SceneNode) => {
          const sceneId = scene.scene_id || (scene as any).id || 'scene';
          const duration = scene.duration_frames || (scene as any).duration_in_frames || 30;
          const layer = scene.render_layer || (scene as any).layout_type || 'kinetic_typography';
          const headline = scene.headline || (scene as any).title || '';

          const show3D = layer === 'three_dimensional' || layer === 'three_d_mesh' || layer === 'hybrid';
          const showKinetic = layer === 'kinetic_typography' || layer === 'hybrid';

          const normalizedScene: any = {
            ...scene,
            id: sceneId,
            scene_id: sceneId,
            duration_in_frames: duration,
            duration_frames: duration,
            title: headline,
            headline: headline,
            icon_asset: scene.icon_asset || 'Zap',
            layout_type: layer,
            render_layer: layer,
          };

          return (
            <Series.Sequence
              key={sceneId}
              durationInFrames={duration}
              name={sceneId}
            >
              <AbsoluteFill>
                {/* 3D WebGL Layer */}
                {show3D && (
                  <ThreeScene
                    threeParams={(scene as any).three_params}
                    theme={normalizedTheme}
                    width={width}
                    height={height}
                  />
                )}

                {/* 2D Kinetic Typography & Dynamic Vector Layer */}
                {showKinetic && (
                  <KineticScene scene={normalizedScene} theme={normalizedTheme} />
                )}
              </AbsoluteFill>
            </Series.Sequence>
          );
        })}
      </Series>
    </AbsoluteFill>
  );
};
