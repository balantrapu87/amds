import React from 'react';
import { Composition } from 'remotion';
import { MainComposition } from './MainComposition';
import { ExplainerSlide, ExplainerSlideProps } from './components/ExplainerSlide';
import { DEFAULT_STORYBOARD, StoryboardContract } from './types/storyboard';
import '@fontsource/inter/400.css';
import '@fontsource/inter/600.css';
import '@fontsource/inter/800.css';

const ExplainerSlidePropsDefault: ExplainerSlideProps = {
  index: 0, total: 5, icon: 'zap', kicker: 'Step 01', title: 'Slide Title', body: 'Explanatory copy goes here.',
};

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="MainComposition"
        component={MainComposition}
        durationInFrames={DEFAULT_STORYBOARD.scenes.reduce((acc, s) => acc + (s.duration_frames || 30), 0)}
        fps={DEFAULT_STORYBOARD.fps}
        width={DEFAULT_STORYBOARD.width}
        height={DEFAULT_STORYBOARD.height}
        defaultProps={DEFAULT_STORYBOARD}
        calculateMetadata={async ({ props }) => {
          const payload = props as StoryboardContract;
          const totalFrames =
            payload?.scenes?.reduce((acc, s) => acc + (s.duration_frames || (s as any).duration_in_frames || 30), 0) || 30;
          return {
            durationInFrames: totalFrames,
            fps: payload?.fps || 30,
            width: payload?.width || 1080,
            height: payload?.height || 1920,
            props: payload,
          };
        }}
      />

      {/* Explainer slide (4:5 social-post canvas) — render with `remotion still`. */}
      <Composition
        id="ExplainerSlide"
        component={ExplainerSlide}
        durationInFrames={1}
        fps={30}
        width={1080}
        height={1350}
        defaultProps={ExplainerSlidePropsDefault}
        calculateMetadata={async ({ props }) => {
          const p = props as Partial<ExplainerSlideProps>;
          return { durationInFrames: 1, fps: 30, width: 1080, height: 1350, props: p };
        }}
      />
    </>
  );
};
