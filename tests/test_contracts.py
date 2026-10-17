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
