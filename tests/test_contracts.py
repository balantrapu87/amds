"""
Contract & Serialization Validation Tests for Autonomous Motion Design Studio.
Ensures Pydantic schemas validate inputs correctly, reject invalid hex colors,
enforce minimum duration bounds, and reject empty scene lists.
"""

import json
import pytest
from pydantic import ValidationError


def test_storyboard_contract_valid_json_parsing():
    """Verify that a valid JSON payload parses correctly into StoryboardContract."""
    from engine.schemas import StoryboardContract, ThemeTokens, SceneNode

    valid_payload = {
        "fps": 30,
        "width": 1080,
        "height": 1920,
        "theme": {
            "background_hex": "#0b0f19",
            "primary_hex": "#38bdf8",
            "text_hex": "#f8fafc",
            "font_family": "Inter",
        },
        "scenes": [
            {
                "scene_id": "scene-01",
                "duration_frames": 30,
                "render_layer": "kinetic_typography",
                "headline": "Autonomous Motion",
                "icon_asset": "Zap",
            }
        ],
    }

    raw_json = json.dumps(valid_payload)
    parsed = StoryboardContract.model_validate_json(raw_json)

    assert parsed.fps == 30
    assert parsed.width == 1080
    assert parsed.height == 1920
    assert parsed.theme.primary_hex == "#38bdf8"
    assert len(parsed.scenes) == 1
    assert parsed.scenes[0].scene_id == "scene-01"
    assert parsed.scenes[0].duration_frames == 30
    assert parsed.scenes[0].render_layer == "kinetic_typography"


def test_invalid_hex_colors_fail():
    """Verify that invalid hex color formats raise a ValidationError."""
    from engine.schemas import ThemeTokens

    with pytest.raises(ValidationError):
        ThemeTokens(primary_hex="not-a-color")

    with pytest.raises(ValidationError):
        ThemeTokens(background_hex="#12345Z")

    with pytest.raises(ValidationError):
        ThemeTokens(text_hex="123456")


def test_negative_or_below_minimum_duration_fails():
    """Verify that negative or sub-minimum durations (< 15 frames) raise a ValidationError."""
    from engine.schemas import SceneNode

    # Negative duration must be rejected
    with pytest.raises(ValidationError):
        SceneNode(
            scene_id="bad_scene_1",
            duration_frames=-10,
            render_layer="kinetic_typography",
            headline="Invalid Negative Duration",
        )

    # Sub-minimum duration (< 15 frames) must be rejected
    with pytest.raises(ValidationError):
        SceneNode(
            scene_id="bad_scene_2",
            duration_frames=10,
            render_layer="kinetic_typography",
            headline="Sub-15 Duration",
        )


def test_empty_scene_list_fails():
    """Verify that a StoryboardContract with an empty scene list raises a ValidationError."""
    from engine.schemas import StoryboardContract, ThemeTokens

    with pytest.raises(ValidationError):
        StoryboardContract(
            fps=30,
            width=1080,
            height=1920,
            theme=ThemeTokens(),
            scenes=[],
        )


# ---------------------------------------------------------------------------
# Script -> TTS -> Audio pipeline contract tests (new capability)
# ---------------------------------------------------------------------------


def test_scene_node_voiceover_contract_round_trip():
    """SceneNode must carry per-scene narration (voiceover_text) and a resolved
    audio_file, and survive a JSON round-trip so Remotion can consume them."""
    from engine.schemas import SceneNode

    node = SceneNode(
        scene_id="scene-vo",
        duration_frames=90,
        render_layer="kinetic_typography",
        headline="Narrated Scene",
        icon_asset="Mic",
        voiceover_text="Welcome to the autonomous motion studio.",
        audio_file="job-123/scene-0.mp3",
    )

    assert node.voiceover_text.startswith("Welcome")
    assert node.audio_file == "job-123/scene-0.mp3"

    dumped = SceneNode.model_validate_json(node.model_dump_json())
    assert dumped.voiceover_text == node.voiceover_text
    assert dumped.audio_file == node.audio_file


def test_scene_node_without_voiceover_still_valid():
    """Backward compatibility: scenes without narration must remain valid."""
    from engine.schemas import SceneNode

    node = SceneNode(
        scene_id="silent",
        duration_frames=60,
        render_layer="kinetic_typography",
        headline="Silent Scene",
    )
    assert node.voiceover_text == ""
    assert node.audio_file is None


def test_tts_module_exposes_synthesize_script():
    """engine.tts must expose an async synthesize_script() and synthesize() driven by local edge-tts."""
    import inspect
    import engine.tts as tts

    assert hasattr(tts, "synthesize_script")
    assert hasattr(tts, "synthesize")
    assert inspect.iscoroutinefunction(tts.synthesize_script)
    # The backend must be the local edge-tts package.
    import edge_tts  # noqa: F401  (raises ImportError if edge-tts is not installed)


def test_audio_mastering_supports_embedded_voiceover():
    """FFmpeg mastering must accept voiceover_embedded=True and omit the separate VO input,
    instead mastering the audio stream that is already muxed into the raw video."""
    from engine.schemas import AudioManifest
    from engine.audio import build_ffmpeg_command

    audio = AudioManifest(voiceover_path="/tmp/does_not_matter.wav")

    # Embedded: raw video already carries the narration -> no VO input, no bgm.
    cmd_embedded = build_ffmpeg_command(
        raw_video_path="/tmp/raw.mp4",
        output_mp4_path="/tmp/out.mp4",
        audio=audio,
        voiceover_embedded=True,
    )
    # The raw video (input 0) is mapped for both video and its embedded audio.
    assert "0:v:0" in cmd_embedded
    # The dummy voiceover file must NOT be added as a separate input.
    assert "/tmp/does_not_matter.wav" not in cmd_embedded


def test_audio_mastering_raw_video_has_audio_helper():
    """engine.audio must expose raw_video_has_audio() for detecting muxed narration."""
    from engine.audio import raw_video_has_audio

    assert callable(raw_video_has_audio)
    # A missing file must report False (no audio), not raise.
    assert raw_video_has_audio("/tmp/definitely_missing_video.mp4") is False
