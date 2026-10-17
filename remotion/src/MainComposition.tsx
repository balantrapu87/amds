import React from 'react';
import { Series, AbsoluteFill, useVideoConfig } from 'remotion';
import { StudioJobPayload, SceneNode } from './types';
import { ThreeScene } from './components/ThreeScene';
import { KineticScene } from './components/KineticScene';
import '@fontsource/inter/400.css';
import '@fontsource/inter/600.css';
import '@fontsource/inter/800.css';

export const MainComposition: React.FC<StudioJobPayload> = (props) => {
  const { theme, scenes } = props;
  const { width, height } = useVideoConfig();

  return (
    <AbsoluteFill
      style={{
        backgroundColor: theme.background_color,
        fontFamily: theme.font_family,
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
          background: `radial-gradient(circle at 50% 40%, ${theme.primary_color}25 0%, ${theme.secondary_color}15 45%, transparent 75%)`,
          pointerEvents: 'none',
        }}
      />

      {/* Sequenced Scene Series */}
      <Series>
        {scenes.map((scene: SceneNode) => {
          const show3D =
            scene.layout_type === 'three_d_mesh' || scene.layout_type === 'hybrid';
          const showKinetic =
            scene.layout_type === 'kinetic_typography' || scene.layout_type === 'hybrid';

          return (
            <Series.Sequence
              key={scene.id}
              durationInFrames={scene.duration_in_frames}
              name={scene.id}
            >
              <AbsoluteFill>
                {/* 3D WebGL Layer */}
                {show3D && (
                  <ThreeScene
                    threeParams={scene.three_params}
                    theme={theme}
                    width={width}
                    height={height}
                  />
                )}

                {/* 2D Kinetic Typography & Dynamic Vector Layer */}
                {showKinetic && (
                  <KineticScene scene={scene} theme={theme} />
                )}
              </AbsoluteFill>
            </Series.Sequence>
          );
        })}
      </Series>
    </AbsoluteFill>
  );
};
