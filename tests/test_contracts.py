"""
Contract & Serialization Validation Tests for Autonomous Motion Design Studio.
Ensures Pydantic schemas validate inputs correctly and generate JSON matching Remotion expectations.
"""

import pytest


def test_schema_import():
    """Verify that schemas module imports cleanly and definitions exist."""
    from engine import schemas
    assert hasattr(schemas, "ThemeTokens")
    assert hasattr(schemas, "SceneNode")
    assert hasattr(schemas, "StudioJobPayload")
    assert hasattr(schemas, "AudioManifest")


def test_theme_tokens_validation():
    """Verify hex color regex and default tokens."""
    from engine.schemas import ThemeTokens

    tokens = ThemeTokens()
    assert tokens.primary_color == "#6366F1"
    assert tokens.border_radius == 16

    # Test invalid hex code rejection
    with pytest.raises(ValueError):
        ThemeTokens(primary_color="invalid-color")

    with pytest.raises(ValueError):
        ThemeTokens(primary_color="#GGGGGG")


def test_scene_node_determinism_contract():
    """Verify SceneNode duration bounds and auto-population of ThreeParams for hybrid/3D scenes."""
    from engine.schemas import SceneNode, SceneLayoutType, ThreeParams

    node = SceneNode(
        id="scene_01",
        duration_in_frames=90,
        layout_type=SceneLayoutType.HYBRID,
        title="Autonomous Motion",
        icon_asset="zap"
    )
    assert node.duration_in_frames == 90
    assert isinstance(node.three_params, ThreeParams)

    # Negative duration must be rejected
    with pytest.raises(ValueError):
        SceneNode(
            id="scene_bad",
            duration_in_frames=-10,
            title="Bad Scene"
        )


def test_studio_job_payload_contract():
    """Verify root container validation."""
    from engine.schemas import StudioJobPayload, SceneNode, AudioManifest, ThemeTokens

    payload = StudioJobPayload(
        job_id="job_test_001",
        theme=ThemeTokens(),
        scenes=[
            SceneNode(
                id="s1",
                duration_in_frames=60,
                title="Scene One"
            )
        ],
        audio=AudioManifest(voiceover_path="/tmp/vo.wav")
    )

    serialized = payload.model_dump_json()
    assert "job_test_001" in serialized
    assert "Scene One" in serialized
