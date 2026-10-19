"""
Local Edge-TTS Voice Synthesis Subsystem.
Converts a per-scene narration script into MP3 voiceover files using the
locally-installed `edge-tts` package (Microsoft neural voices). This is the
script -> audio stage that runs before Remotion video generation.
"""

import os
import logging
from typing import List, Optional, Dict, Any

logger = logging.getLogger("tts_synthesis")

# Default neural voice, overridable via environment variable.
DEFAULT_VOICE = os.getenv("EDGE_TTS_VOICE", "en-US-AriaNeural")


async def synthesize(text: str, out_path: str, voice: str = DEFAULT_VOICE) -> str:
    """Synthesize a single narration text into an MP3 file via local edge-tts."""
    import edge_tts  # imported lazily so the module loads even if edge-tts is absent

    out_dir = os.path.dirname(os.path.abspath(out_path))
    os.makedirs(out_dir, exist_ok=True)
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(out_path)
    logger.info(f"[TTS] synthesized {len(text)} chars -> {out_path} (voice={voice})")
    return out_path


async def synthesize_script(
    scenes: List[Dict[str, Any]],
    audio_root: str,
    job_id: str,
    voice: str = DEFAULT_VOICE,
) -> List[Optional[str]]:
    """Synthesize per-scene narration into <audio_root>/<job_id>/scene-<i>.mp3.

    Returns a list parallel to `scenes` holding the public-relative audio_file
    path (e.g. "<job_id>/scene-0.mp3") for each narrated scene, or None when a
    scene has no voiceover_text or TTS fails for that scene.
    """
    job_dir = os.path.join(audio_root, job_id)
    os.makedirs(job_dir, exist_ok=True)
    results: List[Optional[str]] = []

    for index, scene in enumerate(scenes):
        text = (scene.get("voiceover_text") or "").strip()
        if not text:
            results.append(None)
            continue
        out_path = os.path.join(job_dir, f"scene-{index}.mp3")
        try:
            await synthesize(text, out_path, voice)
            # public-relative path consumed by Remotion staticFile(`audio/${...}`)
            results.append(f"{job_id}/scene-{index}.mp3")
        except Exception as e:  # noqa: BLE001 - TTS must never hard-fail the render
            logger.warning(f"[TTS] scene '{scene.get('scene_id')}' failed: {e}")
            results.append(None)

    return results
