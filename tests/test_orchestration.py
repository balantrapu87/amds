"""
Pipeline orchestration tests: whisper timing, wan clip attachment, ffprobe bound.
All external services mocked — no network, no GPU.
"""
import asyncio

import pytest


def _payload(scenes, fps=30):
    from engine.schemas import StudioJobPayload, AudioManifest
    return StudioJobPayload(
        job_id="job", fps=fps, width=1920, height=1080,
        audio=AudioManifest(voiceover_path="/tmp/x.wav"),
        scenes=scenes,
    )


def _scene(**kw):
    from engine.schemas import SceneNode
    base = dict(scene_id="s1", duration_frames=600, render_layer="kinetic_typography",
                headline="H", voiceover_text="hi")
    base.update(kw)
    return SceneNode(**base)


# ---------------- ffprobe duration bound ----------------

def test_probe_duration_reads_format_duration(monkeypatch):
    import engine.tts as tts

    class R:
        returncode = 0
        stdout = '{"format": {"duration": "3.5"}}'
        stderr = ""

    monkeypatch.setattr(tts.subprocess, "run", lambda *a, **k: R())
    assert tts.probe_duration("x.mp3") == 3.5


def test_probe_duration_raises_on_failure(monkeypatch):
    import engine.tts as tts

    class R:
        returncode = 1
        stdout = ""
        stderr = "no such file"

    monkeypatch.setattr(tts.subprocess, "run", lambda *a, **k: R())
    with pytest.raises(RuntimeError):
        tts.probe_duration("missing.mp3")


# ---------------- whisper timing stage ----------------

def test_apply_whisper_timing_resizes_scene_and_captions(monkeypatch):
    import engine.api as api
    from engine.captions import CaptionError

    scene = _scene(audio_file="audio/job/s1.mp3")
    job = _payload([scene])
    monkeypatch.setattr(api, "transcribe",
                        lambda path, url: {"words": [{"word": " hi", "start": 0.1, "end": 0.9}]})
    monkeypatch.setattr(api, "probe_duration", lambda path: 3.0)
    asyncio.run(api.apply_whisper_timing("job", job))
    assert scene.captions and scene.captions[0].text == "hi"
    # last word end 900ms + 750ms tail = 1650ms -> 50 frames @30fps (probe 3.0s allows)
    assert scene.duration_frames == 50


def test_apply_whisper_timing_caps_at_measured_audio(monkeypatch):
    import engine.api as api

    scene = _scene(duration_frames=600, audio_file="audio/job/s1.mp3")
    job = _payload([scene])
    # whisper claims words end at 2.9s but the MP3 is only 1.0s long
    monkeypatch.setattr(api, "transcribe",
                        lambda path, url: {"words": [{"word": " hi", "start": 2.0, "end": 2.9}]})
    monkeypatch.setattr(api, "probe_duration", lambda path: 1.0)
    asyncio.run(api.apply_whisper_timing("job", job))
    # min(2900+750, 1000) = 1000ms -> 30 frames
    assert scene.duration_frames == 30


def test_apply_whisper_timing_failure_is_non_fatal(monkeypatch):
    import engine.api as api
    from engine.captions import CaptionError

    def boom(path, url):
        raise CaptionError("whisper down")

    scene = _scene(audio_file="audio/job/s1.mp3")
    job = _payload([scene])
    monkeypatch.setattr(api, "transcribe", boom)
    asyncio.run(api.apply_whisper_timing("job", job))
    assert scene.duration_frames == 600  # authored duration kept
    assert scene.captions is None


def test_apply_whisper_timing_skips_scenes_without_audio(monkeypatch):
    import engine.api as api

    scene = _scene()  # no audio_file
    job = _payload([scene])

    def boom(path, url):
        raise AssertionError("transcribe must not be called without audio_file")

    monkeypatch.setattr(api, "transcribe", boom)
    asyncio.run(api.apply_whisper_timing("job", job))
    assert scene.duration_frames == 600


# ---------------- wan clip attachment stage ----------------

class FakeWanClient:
    def __init__(self, base_url, **kw):
        pass

    def close(self):
        pass


def test_attach_wan_clips_generates_and_resolves(monkeypatch):
    import engine.api as api
    from pathlib import Path

    scene = _scene(render_layer="hybrid", duration_frames=150,
                   video_prompts=["a cricket stadium at dusk"])
    job = _payload([scene])

    def fake_gen(client, prompts, w, h, secs, seed, out_dir, fps, **kw):
        p = Path(out_dir) / "scene-0.mp4"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"x")
        return [str(p)]

    monkeypatch.setattr(api, "generate_scene_clips", fake_gen)
    monkeypatch.setattr(api, "WanClient", FakeWanClient)
    asyncio.run(api.attach_wan_clips("job", job))
    assert scene.clips == ["video/job/s1/scene-0.mp4"]


def test_attach_wan_clips_skips_when_clips_present(monkeypatch):
    import engine.api as api

    scene = _scene(render_layer="hybrid",
                   video_prompts=["p"], clips=["video/job/s1/scene-0.mp4"])
    job = _payload([scene])

    def boom(*a, **k):
        raise AssertionError("generation must be skipped when clips exist")

    monkeypatch.setattr(api, "generate_scene_clips", boom)
    monkeypatch.setattr(api, "WanClient", FakeWanClient)
    asyncio.run(api.attach_wan_clips("job", job))
    assert scene.clips == ["video/job/s1/scene-0.mp4"]


def test_attach_wan_clips_skips_without_video_prompts(monkeypatch):
    import engine.api as api

    scene = _scene(render_layer="kinetic_typography")
    job = _payload([scene])

    def boom(*a, **k):
        raise AssertionError("no prompts -> no generation")

    monkeypatch.setattr(api, "generate_scene_clips", boom)
    asyncio.run(api.attach_wan_clips("job", job))
    assert scene.clips is None


def test_attach_wan_clips_hard_stops_on_generation_failure(monkeypatch):
    import engine.api as api
    from engine.video_gen import VideoGenError

    scene = _scene(render_layer="hybrid", duration_frames=150, video_prompts=["p"])
    job = _payload([scene])

    def boom(*a, **k):
        raise VideoGenError("all attempts exhausted")

    monkeypatch.setattr(api, "generate_scene_clips", boom)
    monkeypatch.setattr(api, "WanClient", FakeWanClient)
    with pytest.raises(VideoGenError):
        asyncio.run(api.attach_wan_clips("job", job))
