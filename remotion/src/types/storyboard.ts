/**
 * Foundational Storyboard Contract mirroring Pydantic v2 schemas in engine/schemas.py.
 * Guaranteed 1:1 synchronization between Python orchestrator and Remotion canvas.
 */

export type RenderLayer = 'three_dimensional' | 'kinetic_typography';

export interface ThemeTokens {
  background_hex: string;
  primary_hex: string;
  text_hex: string;
  font_family: string;
}

export interface SceneNode {
  scene_id: string;
  duration_frames: number;
  render_layer: RenderLayer;
  headline: string;
  icon_asset: string;
}

export interface StoryboardContract {
  fps: number;
  width: number;
  height: number;
  theme: ThemeTokens;
  scenes: SceneNode[];
}

export const DEFAULT_THEME_TOKENS: ThemeTokens = {
  background_hex: '#0b0f19',
  primary_hex: '#38bdf8',
  text_hex: '#f8fafc',
  font_family: 'Inter',
};

export const DEFAULT_STORYBOARD: StoryboardContract = {
  fps: 30,
  width: 1080,
  height: 1920,
  theme: DEFAULT_THEME_TOKENS,
  scenes: [
    {
      scene_id: 's1',
      duration_frames: 30,
      render_layer: 'kinetic_typography',
      headline: 'Autonomous Motion Studio',
      icon_asset: 'Zap',
    },
  ],
};
