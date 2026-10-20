"""
Wan 2.1 video generation tests: clip planning, workflow builder, retry policy.
No GPU/network: mocked ComfyUI HTTP via httpx.MockTransport.
"""
import json
import pytest


def _fake_ffmpeg(cmd, *a, **k):
    dest = cmd[-1]
    open(dest, "wb").write(b"fake-mp4")
    return type("R", (), {"returncode": 0})()
# ---------------- clip planning ----------------

def test_plan_clips_tail_is_smallest_4n1_covering_remainder():
    from engine.video_gen import plan_clips
    assert plan_clips(5.06, fps=30) == [81, 73]  # 152f: 81 full + 73 tail (4*18+1)

def test_plan_clips_all_4n_plus_1_and_covers_duration():
    from engine.video_gen import plan_clips
    for seconds in (0.5, 1.0, 2.06, 3.56, 5.0, 5.06, 6.0, 10.0, 13.0, 25.0):
        clips = plan_clips(seconds, fps=30)
        total_s = seconds * 30
        assert all(c % 4 == 1 for c in clips), clips
        assert all(5 <= c <= 81 for c in clips), clips
        assert sum(clips) >= total_s, (seconds, clips)
        # never more than ceil(total/81) + 1 generations
        import math
        assert len(clips) <= math.ceil(total_s / 81) + 1

def test_plan_clips_prefers_full_clips():
    from engine.video_gen import plan_clips
    assert plan_clips(81 / 30, fps=30) == [81]
    # 82 frames: one full + 5-frame tail (5 = 4*1+1)
    assert plan_clips(82 / 30, fps=30) == [81, 5]


# ---------------- latent sizing ----------------

def test_latent_sizing_by_aspect():
    from engine.video_gen import latent_size
    assert latent_size(1920, 1080) == (1216, 704)   # 16:9
    assert latent_size(1080, 1920) == (704, 1216)   # 9:16
    assert latent_size(1350, 1080) == (1216, 704)   # landscape-ish


# ---------------- workflow builder ----------------

def test_build_workflow_structure():
    from engine.video_gen import build_workflow

    wf = build_workflow(
        prompt="A cricket stadium at dusk",
        width=1216, height=704, length=81, seed=42,
        model="wan2.1_t2v_14B_fp8_e4m3fn.safetensors",
        filename_prefix="job-sc1-c0",
    )
    assert set(wf.keys()) == {"37", "38", "39", "40", "6", "7", "3", "8", "47", "28"}
    assert wf["37"]["inputs"]["unet_name"] == "wan2.1_t2v_14B_fp8_e4m3fn.safetensors"
    assert wf["40"]["inputs"] == {"width": 1216, "height": 704, "length": 81, "batch_size": 1}
    assert wf["6"]["inputs"]["text"] == "A cricket stadium at dusk"
    assert wf["3"]["inputs"]["seed"] == 42
    assert wf["3"]["inputs"]["latent_image"] == ["40", 0]
    assert wf["28"]["inputs"]["filename_prefix"] == "job-sc1-c0"


# ---------------- retry policy (mocked ComfyUI) ----------------

def _mock_transport(responses):
    import httpx

    state = {"n": 0}

    def handler(request):
        if request.url.path == "/prompt":
            return httpx.Response(200, json={"prompt_id": f"pid{state['n']}"})
        if request.url.path.startswith("/history/"):
            state["n"] += 1
            item = responses[min(state["n"], len(responses) - 1)]
            if isinstance(item, Exception):
                return httpx.Response(500)
            requested = request.url.path.rsplit("/", 1)[1]
            return httpx.Response(200, json={requested: item})
        if request.url.path == "/view":
            return httpx.Response(200, content=b"fake-webp-bytes")
        return httpx.Response(404)

    return httpx.MockTransport(handler)


def test_generate_clip_succeeds_on_first_try(tmp_path, monkeypatch):
    import httpx
    from engine import video_gen

    monkeypatch.setattr(__import__("time"), "sleep", lambda s: None)
    monkeypatch.setattr(video_gen.subprocess, "run", _fake_ffmpeg)
    transport = _mock_transport([
        {"prompt_id": "pid1", "status": "success",
         "outputs": {"28": {"filename": "job-sc1-c0.webp", "subfolder": "", "type": "output"}}},
    ])
    out = video_gen.WanClient(base_url="http://x", transport=transport)
    path = video_gen.generate_clip(out, "A cricket stadium", 1920, 1080, 81, 42,
                                   str(tmp_path / "c0.mp4"), fps=30)
    assert path.exists()

def test_generate_scene_retries_then_falls_back(tmp_path, monkeypatch):
    import httpx
    from engine import video_gen

    monkeypatch.setattr(__import__("time"), "sleep", lambda s: None)
    monkeypatch.setattr(video_gen.subprocess, "run", _fake_ffmpeg)

    ok = {"prompt_id": "ok", "status": "success",
          "outputs": {"28": {"filename": "f.webp", "subfolder": "", "type": "output"}}}
    fail = {"prompt_id": "f", "status": "error"}
    # 3 failures on primary, then success on fallback
    transport = _mock_transport([fail, fail, fail, fail, fail, fail, ok])
    used = []
    real = video_gen.generate_clip
    def spy(w, p, w2, h, n, s, out, fps, model):
        used.append(model)
        return real(w, p, w2, h, n, s, out, fps, model)
    monkeypatch.setattr(video_gen, "generate_clip", spy)
    video_gen.generate_scene_clips(video_gen.WanClient(base_url="http://x", transport=transport),
                                   prompt="x", job_width=1920, job_height=1080, scene_seconds=2.0,
                                   seed=1, out_dir=tmp_path, fps=30,
                                   primary_model="M14B", fallback_model="M13B")
    assert "M14B" in used and "M13B" in used

def test_generate_scene_hard_error_after_six_attempts(tmp_path, monkeypatch):
    import httpx
    from engine import video_gen

    monkeypatch.setattr(__import__("time"), "sleep", lambda s: None)
    monkeypatch.setattr(video_gen.subprocess, "run", _fake_ffmpeg)
    fail = {"prompt_id": "f", "status": "error"}
    transport = _mock_transport([fail])
    with pytest.raises(video_gen.VideoGenError):
        video_gen.generate_scene_clips(
            video_gen.WanClient(base_url="http://x", transport=transport),
            prompt="x", job_width=1920, job_height=1080, scene_seconds=0.5,
            seed=1, out_dir=tmp_path, fps=30,
            primary_model="M14B", fallback_model="M13B",
        )
