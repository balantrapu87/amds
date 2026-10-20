"""
Whisper word-level caption engine tests (no network: mocked HTTP).
"""
import pathlib
import tempfile

import httpx
import pytest


def test_normalize_words_strips_and_clamps():
    from engine.captions import normalize_words

    raw = [
        {"word": "  Hello  ", "start": 0.12, "end": 0.38},
        {"word": "   ", "start": 0.4, "end": 0.5},
        {"word": "world.", "start": 0.38, "end": 0.9},
    ]
    words = normalize_words(raw)
    assert words == [
        {"text": "Hello", "start_ms": 120, "end_ms": 380},
        {"text": "world.", "start_ms": 380, "end_ms": 900},
    ]


def test_normalize_words_handles_zero_duration_and_missing_end():
    from engine.captions import normalize_words

    raw = [
        {"word": "a", "start": 0.5, "end": 0.5},
        {"word": "b", "start": 1.0},
    ]
    words = normalize_words(raw)
    assert words[0]["end_ms"] > words[0]["start_ms"]
    assert words[1]["end_ms"] > words[1]["start_ms"]


def test_transcribe_posts_verbose_json_with_word_granularity(monkeypatch, tmp_path):
    from engine.captions import transcribe

    calls = {}

    def fake_post(url, files=None, data=None, timeout=None):
        calls["url"] = url
        calls["data"] = data
        calls["has_file"] = "file" in files
        return httpx.Response(
            200,
            json={
                "text": "Hello world.",
                "words": [
                    {"word": " Hello", "start": 0.1, "end": 0.3},
                    {"word": " world.", "start": 0.3, "end": 0.8},
                ],
            },
        )

    monkeypatch.setattr(httpx, "post", fake_post)
    audio = tmp_path / "scene.mp3"
    audio.write_bytes(b"fake-mp3-bytes")

    result = transcribe(str(audio), "http://127.0.0.1:8080/v1/audio/transcriptions")
    assert calls["url"] == "http://127.0.0.1:8080/v1/audio/transcriptions"
    assert calls["data"]["response_format"] == "verbose_json"
    assert "word" in calls["data"]["timestamp_granularities"]
    assert calls["has_file"] is True
    assert result["words"][1]["text" if "text" in result["words"][1] else "word"] == " world."


def test_transcribe_raises_on_http_error(monkeypatch, tmp_path):
    from engine.captions import CaptionError, transcribe

    monkeypatch.setattr(
        httpx, "post", lambda url, files=None, data=None, timeout=None: httpx.Response(500)
    )
    audio = tmp_path / "scene.mp3"
    audio.write_bytes(b"x")
    with pytest.raises(CaptionError):
        transcribe(str(audio), "http://127.0.0.1:8080/v1/audio/transcriptions")


def test_narration_end_is_last_word_end_plus_tail():
    from engine.captions import narration_end_ms

    words = [{"text": "a", "start_ms": 100, "end_ms": 400}]
    assert narration_end_ms(words, tail_ms=750) == 1150
    assert narration_end_ms([], tail_ms=750) == 0


def test_extract_words_top_level():
    from engine.captions import extract_words

    payload = {"text": "Hi.", "words": [{"word": " Hi", "start": 0.1, "end": 0.4}]}
    assert extract_words(payload) == [{"text": "Hi", "start_ms": 100, "end_ms": 400}]


def test_extract_words_nested_in_segments():
    from engine.captions import extract_words

    payload = {
        "text": "Hi there.",
        "segments": [
            {
                "start": 0.0, "end": 1.0, "text": "Hi there.",
                "words": [
                    {"word": " Hi", "start": 0.1, "end": 0.4},
                    {"word": " there.", "start": 0.5, "end": 0.9},
                ],
            }
        ],
    }
    words = extract_words(payload)
    assert [w["text"] for w in words] == ["Hi", "there."]
    assert words[1]["start_ms"] == 500


def test_extract_words_empty_payload():
    from engine.captions import extract_words
    assert extract_words({"text": ""}) == []
