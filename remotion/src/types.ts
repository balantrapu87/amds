/**
 * TypeScript Data Models mirroring Pydantic v2 schemas.
 */

export interface ThemeTokens {
  primary_color: string;
  secondary_color: string;
  accent_color: string;
  background_color: string;
  surface_color: string;
  text_color: string;
  text_muted_color: string;
  font_family: string;
  border_radius: number;
  padding: number;
}

export type SceneLayoutType = 'kinetic_typography' | 'three_d_mesh' | 'hybrid';
export type GeometryType = 'box' | 'sphere' | 'torus' | 'icosahedron' | 'cylinder';

export interface ThreeParams {
  geometry: GeometryType;
  wireframe: boolean;
  color?: string;
  camera_fov: number;
  camera_position: [number, number, number];
  mesh_position: [number, number, number];
  mesh_scale: [number, number, number];
  rotation_speed_x: number;
  rotation_speed_y: number;
  rotation_speed_z: number;
}

export interface CaptionWord {
  text: string;
  start_ms: number;
  end_ms: number;
}

export interface SceneNode {
  id: string;
  frame_start: number;
  duration_in_frames: number;
  layout_type: SceneLayoutType;
  title: string;
  subtitle?: string;
  body_text?: string;
  icon_asset: string;
  svg_overlay_path?: string;
  three_params?: ThreeParams;
  voiceover_text?: string;
  audio_file?: string;
  video_prompts?: string[];
  clips?: string[];
  captions?: CaptionWord[];
}

export interface AudioManifest {
  voiceover_path: string;
  bgm_path?: string;
  target_lufs: number;
  true_peak_db: number;
  ducking_threshold_db: number;
  ducking_ratio: number;
  ducking_attack_ms: number;
  ducking_release_ms: number;
  bgm_volume_db: number;
}

export interface StudioJobPayload {
  job_id: string;
  fps: number;
  width: number;
  height: number;
  theme: ThemeTokens;
  channel_name?: string;
  audio: AudioManifest;
  scenes: SceneNode[];
}

export const DEFAULT_THEME: ThemeTokens = {
  primary_color: '#6366F1',
  secondary_color: '#8B5CF6',
  accent_color: '#06B6D4',
  background_color: '#0F172A',
  surface_color: '#1E293B',
  text_color: '#F8FAFC',
  text_muted_color: '#94A3B8',
  font_family: 'Inter, sans-serif',
  border_radius: 16,
  padding: 32,
};

export const DEFAULT_STUDIO_PAYLOAD: StudioJobPayload = {
  job_id: 'default-preview',
  fps: 30,
  width: 1080,
  height: 1920,
  theme: DEFAULT_THEME,
  audio: {
    voiceover_path: 'assets/voiceover.wav',
    bgm_path: 'assets/bgm.mp3',
    target_lufs: -16.0,
    true_peak_db: -1.5,
    ducking_threshold_db: -20.0,
    ducking_ratio: 4.0,
    ducking_attack_ms: 15.0,
    ducking_release_ms: 250.0,
    bgm_volume_db: -12.0,
  },
  scenes: [
    {
      id: 'scene-01',
      frame_start: 0,
      duration_in_frames: 90,
      layout_type: 'hybrid',
      title: 'Autonomous Motion Studio',
      subtitle: 'Code-driven programmatic video rendering',
      body_text: 'Pure function deterministic frame clocks with zero manual GUI intervention.',
      icon_asset: 'zap',
      three_params: {
        geometry: 'torus',
        wireframe: true,
        camera_fov: 45,
        camera_position: [0, 0, 5],
        mesh_position: [0, 0, 0],
        mesh_scale: [1.2, 1.2, 1.2],
        rotation_speed_x: 0.2,
        rotation_speed_y: 0.6,
        rotation_speed_z: 0.1,
      },
    },
    {
      id: 'scene-02',
      frame_start: 90,
      duration_in_frames: 120,
      layout_type: 'kinetic_typography',
      title: 'GSAP Timelines + Remotion',
      subtitle: 'Stepped frame-by-frame via timeline.seek(frame / fps)',
      body_text: 'Bypassing real-time tickers eliminates frame drops and ensures 100% deterministic exports.',
      icon_asset: 'cpu',
    },
    {
      id: 'scene-03',
      frame_start: 210,
      duration_in_frames: 90,
      layout_type: 'hybrid',
      title: 'EBU R128 Audio Mastering',
      subtitle: 'Automated sidechain compression & ducking filtergraph',
      body_text: 'FFmpeg merges mastered audio with uncompressed video streams directly.',
      icon_asset: 'activity',
      three_params: {
        geometry: 'icosahedron',
        wireframe: true,
        camera_fov: 45,
        camera_position: [0, 0, 5],
        mesh_position: [0, 0, 0],
        mesh_scale: [1.4, 1.4, 1.4],
        rotation_speed_x: 0.3,
        rotation_speed_y: 0.4,
        rotation_speed_z: 0.0,
      },
    },
  ],
};
