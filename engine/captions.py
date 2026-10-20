"""
Whisper word-level caption engine.

POSTs per-scene TTS MP3 to a local OpenAI-compatible Whisper endpoint
(127.0.0.1:8080/v1/audio/transcriptions) with verbose_json + word
granularity, then normalizes word timestamps into CaptionWord dicts.

Whisper is the length authority: narration end = last word end (+ tail).
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class CaptionError(RuntimeError):
    """Raised when the Whisper endpoint fails or returns unusable output."""


def extract_words(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Collect and normalize word timestamps from a Whisper verbose_json payload.

    Handles two layouts:
    - OpenAI standard: a top-level `words` array.
    - llama-swap / local servers: word arrays nested inside each `segments[i].words`.
    """
    raw: List[Dict[str, Any]] = []
    top = payload.get("words")
    if isinstance(top, list):
        raw.extend(top)
    for seg in payload.get("segments") or []:
        nested = seg.get("words") if isinstance(seg, dict) else None
        if isinstance(nested, list):
            raw.extend(nested)
    return normalize_words(raw)


def normalize_words(raw_words: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Convert Whisper verbose_json words into clean CaptionWord dicts.

    - Strips surrounding whitespace from each word.
    - Drops whitespace-only words.
    - Converts seconds -> integer ms, clamps negatives to 0.
    - Guarantees end_ms > start_ms (zero-duration words get 1ms).
    """
    words: List[Dict[str, Any]] = []
    for raw in raw_words or []:
        text = str(raw.get("word") or raw.get("text") or "").strip()
        if not text:
            continue
        start_ms = max(0, int(round(float(raw.get("start", 0.0)) * 1000)))
        end_ms = max(0, int(round(float(raw.get("end", 0.0)) * 1000)))
        if end_ms <= start_ms:
            end_ms = start_ms + 1
        words.append({"text": text, "start_ms": start_ms, "end_ms": end_ms})
    return words


def narration_end_ms(words: List[Dict[str, Any]], tail_ms: int = 750) -> int:
    """Scene narration end = last word end + tail (0 when no words)."""
    if not words:
        return 0
    return words[-1]["end_ms"] + tail_ms


def transcribe(audio_path: str, whisper_url: str, timeout: float = 120.0) -> Dict[str, Any]:
    """Transcribe an MP3 file, returning the parsed Whisper verbose_json payload.

    Raises CaptionError on HTTP failure or missing word timestamps.
    """
    path = Path(audio_path)
    if not path.exists():
        raise CaptionError(f"Audio file not found: {path}")

    with path.open("rb") as fh:
        try:
            resp = httpx.post(
                whisper_url,
                files={"file": fh},
                data={
                    "model": "whisper",
                    "language": "en",
                    "response_format": "verbose_json",
                    "timestamp_granularities": ["word"],
                },
                timeout=timeout,
            )
        except httpx.HTTPError as exc:
            raise CaptionError(f"Whisper request failed: {exc}") from exc

    if resp.status_code != 200:
        raise CaptionError(f"Whisper returned HTTP {resp.status_code}: {resp.text[:200]}")

    payload = resp.json()
    if not isinstance(payload, dict):
        raise CaptionError("Whisper returned a non-object payload.")
    return payload
