"""
Deterministic FFmpeg Audio Mastering Subsystem.
Implements automated sidechain ducking, EBU R128 loudness normalization,
and stream muxing without re-encoding the video track (-c:v copy).
"""

import os
import subprocess
import logging
from typing import Tuple, Optional
from engine.schemas import AudioManifest

logger = logging.getLogger("audio_mastering")


def build_audio_mastering_filtergraph(
    audio: AudioManifest,
    has_bgm: bool = True
) -> Tuple[str, str]:
    """
    Builds the deterministic FFmpeg filter_complex graph and map flags.

    Audio routing architecture:
    Case A (Voiceover + BGM):
      - [1:a] Voiceover track (primary key)
      - [2:a] BGM track
      - [2:a] volume=volume={bgm_volume_db}dB [bgm_scaled]
      - [bgm_scaled][1:a] sidechaincompress=
          threshold={threshold_lin}:
          ratio={ratio}:
          attack={attack_ms}:
          release={release_ms}:
          makeup=1
        [bgm_ducked]
      - [1:a][bgm_ducked] amix=inputs=2:duration=first:dropout_transition=2 [mixed]
      - [mixed] loudnorm=I={target_lufs}:TP={true_peak_db}:LRA=11 [mastered_audio]

    Case B (Voiceover only):
      - [1:a] loudnorm=I={target_lufs}:TP={true_peak_db}:LRA=11 [mastered_audio]
    """
    # Convert threshold from dB to linear amplitude: 10^(dB / 20)
    # ffmpeg sidechaincompress threshold parameter accepts linear (0.000976563 to 1) or dB as e.g. 0.05
    threshold_linear = round(10.0 ** (audio.ducking_threshold_db / 20.0), 6)

    if has_bgm and audio.bgm_path and os.path.exists(audio.bgm_path):
        filter_complex = (
            f"[2:a]volume=volume={audio.bgm_volume_db}dB[bgm_scaled];"
            f"[bgm_scaled][1:a]sidechaincompress="
            f"threshold={threshold_linear}:"
            f"ratio={audio.ducking_ratio}:"
            f"attack={audio.ducking_attack_ms}:"
            f"release={audio.ducking_release_ms}:"
            f"makeup=1[bgm_ducked];"
            f"[1:a][bgm_ducked]amix=inputs=2:duration=first:dropout_transition=2[mixed];"
            f"[mixed]loudnorm=I={audio.target_lufs}:TP={audio.true_peak_db}:LRA=11[mastered_audio]"
        )
    else:
        filter_complex = (
            f"[1:a]loudnorm=I={audio.target_lufs}:TP={audio.true_peak_db}:LRA=11[mastered_audio]"
        )

    return filter_complex, "[mastered_audio]"


def build_ffmpeg_command(
    raw_video_path: str,
    output_mp4_path: str,
    audio: AudioManifest,
) -> list[str]:
    """
    Constructs the exact FFmpeg execution arguments list.
    Preserves video track with `-c:v copy` and masters the dual-channel audio stream.
    """
    has_bgm = bool(audio.bgm_path and os.path.exists(audio.bgm_path))

    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "info"]

    # Input 0: Raw canvas render from Remotion (no audio)
    cmd.extend(["-i", raw_video_path])

    # Input 1: Voiceover track
    cmd.extend(["-i", audio.voiceover_path])

    # Input 2: Optional BGM track
    if has_bgm:
        cmd.extend(["-i", audio.bgm_path])

    # Build filter complex
    filter_complex, audio_out_map = build_audio_mastering_filtergraph(audio, has_bgm)
    cmd.extend(["-filter_complex", filter_complex])

    # Mapping: copy video from input 0, map mastered audio output
    cmd.extend([
        "-map", "0:v:0",
        "-map", audio_out_map,
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "256k",
        "-ar", "48000",
        "-shortest",
        output_mp4_path
    ])

    return cmd


def execute_mastering(
    raw_video_path: str,
    output_mp4_path: str,
    audio: AudioManifest
) -> str:
    """
    Executes the FFmpeg mastering command synchronously and validates output.
    """
    if not os.path.exists(raw_video_path):
        raise FileNotFoundError(f"Raw video path does not exist: {raw_video_path}")
    if not os.path.exists(audio.voiceover_path):
        raise FileNotFoundError(f"Voiceover path does not exist: {audio.voiceover_path}")

    os.makedirs(os.path.dirname(os.path.abspath(output_mp4_path)), exist_ok=True)
    cmd = build_ffmpeg_command(raw_video_path, output_mp4_path, audio)
    cmd_str = " ".join(cmd)
    logger.info(f"Executing FFmpeg mastering command:\n{cmd_str}")

    process = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False
    )

    if process.returncode != 0:
        logger.error(f"FFmpeg mastering failed with code {process.returncode}:\n{process.stderr}")
        raise RuntimeError(f"FFmpeg mastering failed: {process.stderr[-500:]}")

    logger.info(f"Mastering complete. Final video saved at: {output_mp4_path}")
    return output_mp4_path
