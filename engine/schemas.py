"""
Pydantic v2 Data Models for Autonomous Motion Design Studio.
Defines foundational contracts for ThemeTokens, SceneNode, and StoryboardContract,
alongside audio mastering contracts and execution payloads.
"""

from enum import Enum
from typing import List, Optional, Tuple, Literal
import re
from pydantic import BaseModel, Field, field_validator, model_validator


HEX_COLOR_REGEX = re.compile(r"^#(?:[0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")


class ThemeTokens(BaseModel):
    """Visual design tokens defining the chromatic and typographic system."""
    background_hex: str = Field(default="#0b0f19", description="Base background color (hex)")
    primary_hex: str = Field(default="#38bdf8", description="Primary brand color (hex)")
    text_hex: str = Field(default="#f8fafc", description="Primary typography color (hex)")
    font_family: str = Field(default="Inter", description="Font family rule")

    # Optional design tokens for extended surfaces
    secondary_color: Optional[str] = Field(default="#8B5CF6", description="Secondary accent color (hex)")
    accent_color: Optional[str] = Field(default="#06B6D4", description="Highlight accent color (hex)")
    surface_color: Optional[str] = Field(default="#1E293B", description="Card/Surface container color (hex)")
    text_muted_color: Optional[str] = Field(default="#94A3B8", description="Secondary typography color (hex)")
    border_radius: int = Field(default=16, ge=0, le=64, description="Border radius in pixels")
    padding: int = Field(default=32, ge=8, le=128, description="Base padding in pixels")

    @field_validator(
        "background_hex",
        "primary_hex",
        "text_hex",
    )
    @classmethod
    def validate_hex_color(cls, v: str) -> str:
        if not HEX_COLOR_REGEX.match(v):
            raise ValueError(f"Color '{v}' is not a valid hex string (#RGB, #RRGGBB, or #RRGGBBAA).")
        return v

    @field_validator(
        "secondary_color",
        "accent_color",
        "surface_color",
        "text_muted_color",
    )
    @classmethod
    def validate_optional_hex(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not HEX_COLOR_REGEX.match(v):
            raise ValueError(f"Color '{v}' is not a valid hex string.")
        return v

    @property
    def primary_color(self) -> str:
        return self.primary_hex

    @property
    def background_color(self) -> str:
        return self.background_hex

    @property
    def text_color(self) -> str:
        return self.text_hex


RenderLayer = Literal[
    "kinetic_typography", "three_dimensional", "hybrid", "three_d_mesh"
]


class CaptionWord(BaseModel):
    """A single word-level caption timestamp (scene-relative, milliseconds)."""
    text: str = Field(..., min_length=1, description="Word or punctuation chunk to display")
    start_ms: int = Field(..., ge=0, description="Word start offset in ms from scene start")
    end_ms: int = Field(..., ge=1, description="Word end offset in ms from scene start")

    @model_validator(mode="after")
    def check_word_timing(self) -> "CaptionWord":
        if self.end_ms <= self.start_ms:
            raise ValueError("Caption word end_ms must be strictly greater than start_ms.")
        return self


class SceneNode(BaseModel):
    """Individual scene specification within the timeline."""
    scene_id: str = Field(..., min_length=1, description="Unique scene identifier")
    duration_frames: int = Field(..., ge=15, le=1800, description="Scene duration in frames (minimum 15)")
    render_layer: RenderLayer = Field(
        default="kinetic_typography", description="Render layer engine mode"
    )
    headline: str = Field(..., min_length=1, max_length=120, description="Primary header copy")
    subtitle: Optional[str] = Field(default=None, max_length=200, description="Secondary header copy")
    body_text: Optional[str] = Field(default=None, description="Narrative body copy for the scene")
    icon_asset: str = Field(default="Zap", description="Lucide icon name identifier")
    three_params: Optional["ThreeParams"] = Field(
        default=None, description="3D mesh/camera parameters for three_dimensional, hybrid, or three_d_mesh layers"
    )
    voiceover_text: str = Field(default="", description="Narration script for this scene (TTS input)")
    audio_file: Optional[str] = Field(default=None, description="Resolved TTS audio file path relative to remotion/public/")
    video_prompts: Optional[List[str]] = Field(default=None, description="Per-clip text-to-video prompts (Wan 2.1 input)")
    clips: Optional[List[str]] = Field(default=None, description="Resolved generated video clip paths relative to remotion/public/")
    clip_frames: Optional[List[int]] = Field(default=None, description="Exact frame length of each clip (parallel to clips)")
    captions: Optional[List[CaptionWord]] = Field(default=None, description="Word-level karaoke caption timestamps")

    # Compatibility properties for composition pipelines
    @property
    def id(self) -> str:
        return self.scene_id

    @property
    def duration_in_frames(self) -> int:
        return self.duration_frames

    @property
    def title(self) -> str:
        return self.headline

    @property
    def layout_type(self) -> str:
        return self.render_layer


class StoryboardContract(BaseModel):
    """Foundational storyboard contract governing deterministic video rendering."""
    fps: int = Field(default=30, ge=1, le=120, description="Video frame rate (fps)")
    width: int = Field(default=1080, ge=480, le=3840, description="Video output width in pixels")
    height: int = Field(default=1920, ge=480, le=3840, description="Video output height in pixels")
    theme: ThemeTokens = Field(default_factory=ThemeTokens, description="Visual theme tokens")
    scenes: List[SceneNode] = Field(..., min_length=1, max_length=50, description="Ordered timeline scenes")

    @property
    def total_duration_frames(self) -> int:
        return sum(scene.duration_frames for scene in self.scenes)

    @property
    def total_duration_seconds(self) -> float:
        return self.total_duration_frames / self.fps


class SceneLayoutType(str, Enum):
    KINETIC_TYPOGRAPHY = "kinetic_typography"
    THREE_D_MESH = "three_d_mesh"
    HYBRID = "hybrid"


class GeometryType(str, Enum):
    BOX = "box"
    SPHERE = "sphere"
    TORUS = "torus"
    ICOSAHEDRON = "icosahedron"
    CYLINDER = "cylinder"


class ThreeParams(BaseModel):
    """Three.js camera and geometry parameters for deterministic 3D scenes."""
    geometry: GeometryType = Field(default=GeometryType.TORUS, description="Mesh geometry type")
    wireframe: bool = Field(default=True, description="Render wireframe vs solid material")
    color: Optional[str] = Field(default=None, description="Optional override color (hex)")
    camera_fov: float = Field(default=45.0, ge=15.0, le=120.0, description="Camera Field of View")
    camera_position: Tuple[float, float, float] = Field(default=(0.0, 0.0, 5.0), description="[x, y, z] camera origin")
    mesh_position: Tuple[float, float, float] = Field(default=(0.0, 0.0, 0.0), description="[x, y, z] mesh position")
    mesh_scale: Tuple[float, float, float] = Field(default=(1.0, 1.0, 1.0), description="[sx, sy, sz] mesh scale")
    rotation_speed_x: float = Field(default=0.2, description="Rotations per second around X axis")
    rotation_speed_y: float = Field(default=0.5, description="Rotations per second around Y axis")
    rotation_speed_z: float = Field(default=0.0, description="Rotations per second around Z axis")


# Resolve the SceneNode.three_params forward reference now that ThreeParams is defined.
SceneNode.model_rebuild()


class AudioManifest(BaseModel):
    """Audio configuration and sidechain ducking mastering contract."""
    voiceover_path: str = Field(..., description="Path to voiceover audio file (wav or mp3)")
    bgm_path: Optional[str] = Field(default=None, description="Path to background music audio file")
    target_lufs: float = Field(default=-16.0, ge=-24.0, le=-9.0, description="EBU R128 integrated loudness target")
    true_peak_db: float = Field(default=-1.5, ge=-6.0, le=0.0, description="Max true peak limit in dBTP")
    ducking_threshold_db: float = Field(default=-20.0, ge=-40.0, le=-6.0, description="Sidechain compressor threshold in dB")
    ducking_ratio: float = Field(default=4.0, ge=1.5, le=20.0, description="Sidechain compression ratio")
    ducking_attack_ms: float = Field(default=15.0, ge=1.0, le=100.0, description="Sidechain attack time in ms")
    ducking_release_ms: float = Field(default=250.0, ge=50.0, le=1000.0, description="Sidechain release recovery time in ms")
    bgm_volume_db: float = Field(default=-12.0, ge=-30.0, le=0.0, description="Baseline BGM gain adjustment before ducking")


class StudioJobPayload(BaseModel):
    """Root container payload submitted to the Remotion renderer and audio mastering engine."""
    job_id: str = Field(..., description="Unique UUID or slug identifier for the render job")
    fps: int = Field(default=30, ge=24, le=60, description="Video frame rate (fps)")
    width: int = Field(default=1080, ge=480, le=3840, description="Video output width in pixels")
    height: int = Field(default=1920, ge=480, le=3840, description="Video output height in pixels")
    theme: ThemeTokens = Field(default_factory=ThemeTokens, description="Visual theme tokens")
    channel_name: Optional[str] = Field(default="T20CRICTANK", max_length=60, description="Brand channel name shown on video scenes")
    audio: AudioManifest = Field(..., description="Audio assets and ducking parameters")
    scenes: List[SceneNode] = Field(..., min_length=1, max_length=50, description="Ordered timeline scenes")

    @property
    def total_duration_in_frames(self) -> int:
        return sum(scene.duration_frames for scene in self.scenes)

    @property
    def total_duration_seconds(self) -> float:
        return self.total_duration_in_frames / self.fps


class RenderRequest(BaseModel):
    """Incoming request payload to POST /render."""
    brief: Optional[str] = Field(default=None, description="Natural language topic brief if autonomous storyboard is needed")
    payload: Optional[StudioJobPayload] = Field(default=None, description="Explicit pre-compiled StudioJobPayload")
    voiceover_path: Optional[str] = Field(default=None, description="Voiceover file path when using topic brief")
    bgm_path: Optional[str] = Field(default=None, description="BGM file path when using topic brief")
    width: int = Field(default=1080, description="Width (1080 for 9:16 vertical, 1920 for 16:9 widescreen)")
    height: int = Field(default=1920, description="Height (1920 for 9:16 vertical, 1080 for 16:9 widescreen)")
    fps: int = Field(default=30, description="Frames per second")

    @model_validator(mode="after")
    def check_brief_or_payload(self) -> "RenderRequest":
        if not self.brief and not self.payload:
            raise ValueError("Either 'brief' or 'payload' must be provided.")
        return self
