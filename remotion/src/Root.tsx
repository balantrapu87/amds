import React from 'react';
import { Composition } from 'remotion';
import { MainComposition } from './MainComposition';
import { DEFAULT_STORYBOARD, StoryboardContract } from './types/storyboard';

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="MainComposition"
        component={MainComposition}
        durationInFrames={DEFAULT_STORYBOARD.scenes.reduce(
          (acc, s) => acc + (s.duration_frames || 30),
          0
        )}
        fps={DEFAULT_STORYBOARD.fps}
        width={DEFAULT_STORYBOARD.width}
        height={DEFAULT_STORYBOARD.height}
        defaultProps={DEFAULT_STORYBOARD}
        calculateMetadata={async ({ props }) => {
          const payload = props as StoryboardContract;
          const totalFrames =
            payload?.scenes?.reduce(
              (acc, s) => acc + (s.duration_frames || (s as any).duration_in_frames || 30),
              0
            ) || 30;

          return {
            durationInFrames: totalFrames,
            fps: payload?.fps || 30,
            width: payload?.width || 1080,
            height: payload?.height || 1920,
            props: payload,
          };
        }}
      />
    </>
  );
};
