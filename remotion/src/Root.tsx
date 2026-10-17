import React from 'react';
import { Composition } from 'remotion';
import { MainComposition } from './MainComposition';
import { DEFAULT_STUDIO_PAYLOAD, StudioJobPayload } from './types';

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="MainComposition"
        component={MainComposition}
        durationInFrames={DEFAULT_STUDIO_PAYLOAD.scenes.reduce(
          (acc, s) => acc + s.duration_in_frames,
          0
        )}
        fps={DEFAULT_STUDIO_PAYLOAD.fps}
        width={DEFAULT_STUDIO_PAYLOAD.width}
        height={DEFAULT_STUDIO_PAYLOAD.height}
        defaultProps={DEFAULT_STUDIO_PAYLOAD}
        calculateMetadata={async ({ props }) => {
          const payload = props as StudioJobPayload;
          const totalFrames =
            payload?.scenes?.reduce((acc, s) => acc + s.duration_in_frames, 0) ||
            300;

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
