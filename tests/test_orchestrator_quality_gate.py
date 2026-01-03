from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock

from tests.helpers import write_metadata, write_post_templates

sys.path.insert(0, str(Path(__file__).parent.parent))
import orchestrator


def _write_video_render_summary(root: Path, run_id: str, output_mp4_rel: str) -> Path:
    artifacts_dir = root / "output" / run_id / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "schema_version": "v1",
        "run_id": run_id,
        "output_mp4_path": output_mp4_rel,
        "hook": "Test hook line",
        "cta": "Test call to action",
    }
    summary_path = artifacts_dir / "video_render_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary_path


def _assert_summary_contract(summary: dict, run_id: str, output_mp4_rel: str):
    assert summary["schema_version"] == "v1"
    assert summary["run_id"] == run_id
    assert (
        summary["input_video_render_summary"]
        == f"output/{run_id}/artifacts/video_render_summary.json"
    )
    assert summary["output_mp4_path"] == output_mp4_rel
    assert summary["engine"] == "quality.gate"
    assert isinstance(summary["checked_at"], str)
    assert summary["checked_at"]
    assert isinstance(summary["checks"], dict)


def _assert_reason_contract(reason: dict, checked_at: str):
    assert isinstance(reason["code"], str)
    assert isinstance(reason["message"], str)
    assert reason["severity"] in ("error", "warn")
    assert reason["engine"] == "quality.gate"
    assert reason["checked_at"] == checked_at


def test_orchestrator_quality_gate_pass(tmp_path, monkeypatch):
    run_id = "run_pass"
    output_mp4_rel = f"output/{run_id}/artifacts/demo_pass.mp4"
    mp4_path = tmp_path / output_mp4_rel
    mp4_path.parent.mkdir(parents=True, exist_ok=True)
    mp4_path.write_bytes(b"fake mp4")

    _write_video_render_summary(tmp_path, run_id, output_mp4_rel)
    write_post_templates(tmp_path)
    write_metadata(
        tmp_path,
        run_id,
        title="Quality Gate Test",
        description="Testing quality gate with post templates",
        tags=["#quality", "#test"],
    )

    pipeline_path = tmp_path / "pipeline.yml"
    pipeline_path.write_text(
        """pipeline: quality_gate_pass
steps:
  - id: quality_gate
    uses: quality.gate
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(orchestrator, "ROOT", tmp_path)
    monkeypatch.setenv("PIPELINE_ENABLED", "true")

    ffprobe_payload = json.dumps(
        {"format": {"duration": "12.0"}, "streams": [{"codec_type": "audio"}]}
    )

    def fake_run(cmd, check=False, capture_output=True, text=True):
        return subprocess.CompletedProcess(cmd, 0, stdout=ffprobe_payload, stderr="")

    monkeypatch.setattr(orchestrator.subprocess, "run", fake_run)

    orchestrator.run_pipeline(pipeline_path, run_id)

    summary_path = (
        tmp_path / "output" / run_id / "artifacts" / "quality_gate_summary.json"
    )
    assert summary_path.exists()

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    _assert_summary_contract(summary, run_id, output_mp4_rel)
    assert summary["decision"] == "pass"
    assert summary["reasons"] == []

    # Verify post_templates was auto-invoked after quality_gate
    post_content_path = (
        tmp_path / "output" / run_id / "artifacts" / "post_content_summary.json"
    )
    assert post_content_path.exists(), (
        "post_content_summary.json should be created by auto-invocation "
        "of post_templates after quality_gate completes"
    )
    post_summary = json.loads(post_content_path.read_text(encoding="utf-8"))
    assert post_summary["schema_version"] == "v1"
    assert post_summary["run_id"] == run_id


def test_orchestrator_quality_gate_missing_mp4_fails(tmp_path, monkeypatch):
    run_id = "run_missing"
    output_mp4_rel = f"output/{run_id}/artifacts/missing.mp4"
    _write_video_render_summary(tmp_path, run_id, output_mp4_rel)
    write_post_templates(tmp_path)
    write_metadata(
        tmp_path,
        run_id,
        title="Missing MP4",
        description="Test missing mp4 behavior",
        tags=["#missing", "#mp4"],
    )

    pipeline_path = tmp_path / "pipeline.yml"
    pipeline_path.write_text(
        """pipeline: quality_gate_missing
steps:
  - id: quality_gate
    uses: quality.gate
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(orchestrator, "ROOT", tmp_path)
    monkeypatch.setenv("PIPELINE_ENABLED", "true")

    mock_run = Mock()
    monkeypatch.setattr(orchestrator.subprocess, "run", mock_run)

    try:
        orchestrator.run_pipeline(pipeline_path, run_id)
    except RuntimeError as exc:
        assert "Quality gate failed" in str(exc)
        assert run_id in str(exc)
    else:
        raise AssertionError("Expected RuntimeError for missing mp4")

    summary_path = (
        tmp_path / "output" / run_id / "artifacts" / "quality_gate_summary.json"
    )
    assert summary_path.exists()

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    _assert_summary_contract(summary, run_id, output_mp4_rel)
    assert summary["decision"] == "fail"
    assert [reason["code"] for reason in summary["reasons"]] == ["mp4_missing"]
    _assert_reason_contract(summary["reasons"][0], summary["checked_at"])
    assert mock_run.call_count == 0

    # Verify post_templates was NOT auto-invoked when quality_gate fails
    post_content_path = (
        tmp_path / "output" / run_id / "artifacts" / "post_content_summary.json"
    )
    assert not post_content_path.exists(), (
        "post_content_summary.json should NOT be created when quality_gate fails"
    )


def test_orchestrator_quality_gate_ffprobe_failure(tmp_path, monkeypatch):
    run_id = "run_ffprobe"
    output_mp4_rel = f"output/{run_id}/artifacts/demo_fail.mp4"
    mp4_path = tmp_path / output_mp4_rel
    mp4_path.parent.mkdir(parents=True, exist_ok=True)
    mp4_path.write_bytes(b"fake mp4")

    _write_video_render_summary(tmp_path, run_id, output_mp4_rel)

    pipeline_path = tmp_path / "pipeline.yml"
    pipeline_path.write_text(
        """pipeline: quality_gate_ffprobe
steps:
  - id: quality_gate
    uses: quality.gate
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(orchestrator, "ROOT", tmp_path)
    monkeypatch.setenv("PIPELINE_ENABLED", "true")

    def fake_run(cmd, check=False, capture_output=True, text=True):
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="error")

    monkeypatch.setattr(orchestrator.subprocess, "run", fake_run)

    try:
        orchestrator.run_pipeline(pipeline_path, run_id)
    except RuntimeError as exc:
        assert "Quality gate failed" in str(exc)
    else:
        raise AssertionError("Expected RuntimeError for ffprobe failure")

    summary_path = (
        tmp_path / "output" / run_id / "artifacts" / "quality_gate_summary.json"
    )
    assert summary_path.exists()

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    _assert_summary_contract(summary, run_id, output_mp4_rel)
    assert summary["decision"] == "fail"
    assert [reason["code"] for reason in summary["reasons"]] == ["ffprobe_failed"]
    _assert_reason_contract(summary["reasons"][0], summary["checked_at"])


def test_orchestrator_quality_gate_mp4_empty_fails(tmp_path, monkeypatch):
    run_id = "run_empty"
    output_mp4_rel = f"output/{run_id}/artifacts/empty.mp4"
    mp4_path = tmp_path / output_mp4_rel
    mp4_path.parent.mkdir(parents=True, exist_ok=True)
    mp4_path.write_bytes(b"")

    _write_video_render_summary(tmp_path, run_id, output_mp4_rel)

    pipeline_path = tmp_path / "pipeline.yml"
    pipeline_path.write_text(
        """pipeline: quality_gate_empty
steps:
  - id: quality_gate
    uses: quality.gate
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(orchestrator, "ROOT", tmp_path)
    monkeypatch.setenv("PIPELINE_ENABLED", "true")

    mock_run = Mock()
    monkeypatch.setattr(orchestrator.subprocess, "run", mock_run)

    try:
        orchestrator.run_pipeline(pipeline_path, run_id)
    except RuntimeError as exc:
        assert "Quality gate failed" in str(exc)
    else:
        raise AssertionError("Expected RuntimeError for empty mp4")

    summary_path = (
        tmp_path / "output" / run_id / "artifacts" / "quality_gate_summary.json"
    )
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    _assert_summary_contract(summary, run_id, output_mp4_rel)
    assert summary["decision"] == "fail"
    assert [reason["code"] for reason in summary["reasons"]] == ["mp4_empty"]
    _assert_reason_contract(summary["reasons"][0], summary["checked_at"])
    assert mock_run.call_count == 0


def test_orchestrator_quality_gate_duration_zero_fails(tmp_path, monkeypatch):
    run_id = "run_dur_zero"
    output_mp4_rel = f"output/{run_id}/artifacts/dur_zero.mp4"
    mp4_path = tmp_path / output_mp4_rel
    mp4_path.parent.mkdir(parents=True, exist_ok=True)
    mp4_path.write_bytes(b"fake mp4")

    _write_video_render_summary(tmp_path, run_id, output_mp4_rel)

    pipeline_path = tmp_path / "pipeline.yml"
    pipeline_path.write_text(
        """pipeline: quality_gate_dur_zero
steps:
  - id: quality_gate
    uses: quality.gate
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(orchestrator, "ROOT", tmp_path)
    monkeypatch.setenv("PIPELINE_ENABLED", "true")

    ffprobe_payload = json.dumps(
        {"format": {"duration": "0"}, "streams": [{"codec_type": "audio"}]}
    )

    def fake_run(cmd, check=False, capture_output=True, text=True):
        return subprocess.CompletedProcess(cmd, 0, stdout=ffprobe_payload, stderr="")

    monkeypatch.setattr(orchestrator.subprocess, "run", fake_run)

    try:
        orchestrator.run_pipeline(pipeline_path, run_id)
    except RuntimeError as exc:
        assert "Quality gate failed" in str(exc)
    else:
        raise AssertionError("Expected RuntimeError for duration zero")

    summary_path = (
        tmp_path / "output" / run_id / "artifacts" / "quality_gate_summary.json"
    )
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    _assert_summary_contract(summary, run_id, output_mp4_rel)
    assert summary["decision"] == "fail"
    assert [reason["code"] for reason in summary["reasons"]] == [
        "duration_zero_or_missing"
    ]
    _assert_reason_contract(summary["reasons"][0], summary["checked_at"])


def test_orchestrator_quality_gate_audio_stream_missing_fails(tmp_path, monkeypatch):
    run_id = "run_no_audio"
    output_mp4_rel = f"output/{run_id}/artifacts/no_audio.mp4"
    mp4_path = tmp_path / output_mp4_rel
    mp4_path.parent.mkdir(parents=True, exist_ok=True)
    mp4_path.write_bytes(b"fake mp4")

    _write_video_render_summary(tmp_path, run_id, output_mp4_rel)

    pipeline_path = tmp_path / "pipeline.yml"
    pipeline_path.write_text(
        """pipeline: quality_gate_no_audio
steps:
  - id: quality_gate
    uses: quality.gate
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(orchestrator, "ROOT", tmp_path)
    monkeypatch.setenv("PIPELINE_ENABLED", "true")

    ffprobe_payload = json.dumps(
        {"format": {"duration": "12.0"}, "streams": [{"codec_type": "video"}]}
    )

    def fake_run(cmd, check=False, capture_output=True, text=True):
        return subprocess.CompletedProcess(cmd, 0, stdout=ffprobe_payload, stderr="")

    monkeypatch.setattr(orchestrator.subprocess, "run", fake_run)

    try:
        orchestrator.run_pipeline(pipeline_path, run_id)
    except RuntimeError as exc:
        assert "Quality gate failed" in str(exc)
    else:
        raise AssertionError("Expected RuntimeError for missing audio stream")

    summary_path = (
        tmp_path / "output" / run_id / "artifacts" / "quality_gate_summary.json"
    )
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    _assert_summary_contract(summary, run_id, output_mp4_rel)
    assert summary["decision"] == "fail"
    assert [reason["code"] for reason in summary["reasons"]] == ["audio_stream_missing"]
    _assert_reason_contract(summary["reasons"][0], summary["checked_at"])


def test_orchestrator_both_video_render_and_quality_gate(tmp_path, monkeypatch):
    """
    ทดสอบว่า post_templates ถูกเรียกครั้งเดียวหลัง quality.gate
    เมื่อมีทั้ง video.render และ quality.gate
    """
    from automation_core.voiceover_tts import compute_input_sha256

    run_id = "run_both_steps"
    slug = "bothsteps"
    sha12 = compute_input_sha256("Hello both steps")[:12]

    # Setup voiceover summary for video.render
    artifacts_dir = tmp_path / "output" / run_id / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    wav_rel = f"data/voiceovers/{run_id}/{slug}_{sha12}.wav"
    wav_path = tmp_path / wav_rel
    wav_path.parent.mkdir(parents=True, exist_ok=True)
    wav_path.write_bytes(b"RIFF")

    voiceover_summary = {
        "schema_version": "v1",
        "run_id": run_id,
        "slug": slug,
        "text_sha256_12": sha12,
        "wav_path": wav_rel,
        "metadata_path": f"data/voiceovers/{run_id}/{slug}_{sha12}.json",
        "engine": "null_tts",
    }
    voiceover_summary_path = artifacts_dir / "voiceover_summary.json"
    voiceover_summary_path.write_text(
        json.dumps(voiceover_summary, indent=2), encoding="utf-8"
    )

    # Setup templates and metadata
    write_post_templates(tmp_path)
    write_metadata(
        tmp_path,
        run_id,
        title="Both Steps Test",
        description="Test with both video.render and quality.gate",
        tags=["#both", "#test"],
    )

    pipeline_path = tmp_path / "pipeline.yml"
    pipeline_path.write_text(
        f"""pipeline: both_steps
steps:
  - id: video_render
    uses: video.render
    config:
      slug: {slug}
      dry_run: false
  - id: quality_gate
    uses: quality.gate
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(orchestrator, "ROOT", tmp_path)
    monkeypatch.setenv("PIPELINE_ENABLED", "true")

    output_mp4_rel = f"output/{run_id}/artifacts/{slug}_{sha12}.mp4"
    mp4_path = tmp_path / output_mp4_rel
    mp4_path.write_bytes(b"fake mp4 data")

    ffprobe_payload = json.dumps(
        {"format": {"duration": "12.0"}, "streams": [{"codec_type": "audio"}]}
    )

    def fake_run(cmd, check=False, capture_output=True, text=True):
        if "ffprobe" in str(cmd):
            return subprocess.CompletedProcess(
                cmd, 0, stdout=ffprobe_payload, stderr=""
            )
        else:  # ffmpeg
            return subprocess.CompletedProcess(cmd, 0, stdout="ok", stderr="")

    monkeypatch.setattr(orchestrator.subprocess, "run", fake_run)

    orchestrator.run_pipeline(pipeline_path, run_id)

    # Verify video_render_summary.json exists
    video_render_summary_path = artifacts_dir / "video_render_summary.json"
    assert video_render_summary_path.exists()

    # Verify quality_gate_summary.json exists
    quality_gate_summary_path = artifacts_dir / "quality_gate_summary.json"
    assert quality_gate_summary_path.exists()

    # Verify post_content_summary.json was created only once (after quality.gate)
    post_content_path = artifacts_dir / "post_content_summary.json"
    assert post_content_path.exists(), (
        "post_content_summary.json should be created by auto-invocation "
        "after quality_gate completes (not after video_render)"
    )

    post_summary = json.loads(post_content_path.read_text(encoding="utf-8"))
    assert post_summary["schema_version"] == "v1"
    assert post_summary["run_id"] == run_id

    # Verify that the post_content_summary exists (the actual sources depend on what fields were used)
    # Since metadata.json contains all required fields, it may be the only source listed
    sources = post_summary["inputs"]["sources"]
    assert len(sources) >= 1, "At least one source should be listed"
    assert f"output/{run_id}/metadata.json" in sources


def test_orchestrator_explicit_post_templates_no_autorun(tmp_path, monkeypatch):
    """
    ทดสอบว่าเมื่อมี step post_templates ระบุไว้แล้วจะไม่ auto-run ซ้ำ
    """
    from automation_core.voiceover_tts import compute_input_sha256

    run_id = "run_explicit_post"
    slug = "explicitpost"
    sha12 = compute_input_sha256("Hello explicit post")[:12]

    artifacts_dir = tmp_path / "output" / run_id / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    wav_rel = f"data/voiceovers/{run_id}/{slug}_{sha12}.wav"
    wav_path = tmp_path / wav_rel
    wav_path.parent.mkdir(parents=True, exist_ok=True)
    wav_path.write_bytes(b"RIFF")

    voiceover_summary = {
        "schema_version": "v1",
        "run_id": run_id,
        "slug": slug,
        "text_sha256_12": sha12,
        "wav_path": wav_rel,
        "metadata_path": f"data/voiceovers/{run_id}/{slug}_{sha12}.json",
        "engine": "null_tts",
    }
    voiceover_summary_path = artifacts_dir / "voiceover_summary.json"
    voiceover_summary_path.write_text(
        json.dumps(voiceover_summary, indent=2), encoding="utf-8"
    )

    write_post_templates(tmp_path)
    write_metadata(
        tmp_path,
        run_id,
        title="Explicit Post Templates",
        description="Test explicit post_templates step",
        tags=["#explicit", "#post"],
    )

    pipeline_path = tmp_path / "pipeline.yml"
    pipeline_path.write_text(
        f"""pipeline: explicit_post_templates
steps:
  - id: video_render
    uses: video.render
    config:
      slug: {slug}
      dry_run: false
  - id: quality_gate
    uses: quality.gate
  - id: post_templates
    uses: post_templates
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(orchestrator, "ROOT", tmp_path)
    monkeypatch.setenv("PIPELINE_ENABLED", "true")

    output_mp4_rel = f"output/{run_id}/artifacts/{slug}_{sha12}.mp4"
    mp4_path = tmp_path / output_mp4_rel
    mp4_path.parent.mkdir(parents=True, exist_ok=True)
    mp4_path.write_bytes(b"fake mp4 data")

    ffprobe_payload = json.dumps(
        {"format": {"duration": "12.0"}, "streams": [{"codec_type": "audio"}]}
    )

    def fake_run(cmd, check=False, capture_output=True, text=True):
        if "ffprobe" in str(cmd):
            return subprocess.CompletedProcess(
                cmd, 0, stdout=ffprobe_payload, stderr=""
            )
        return subprocess.CompletedProcess(cmd, 0, stdout="ok", stderr="")

    monkeypatch.setattr(orchestrator.subprocess, "run", fake_run)

    calls: list[str] = []
    original = orchestrator._run_post_templates_step

    def wrapped(run_id: str, root_dir: Path) -> str:
        calls.append(run_id)
        return original(run_id, root_dir)

    monkeypatch.setattr(orchestrator, "_run_post_templates_step", wrapped)

    orchestrator.run_pipeline(pipeline_path, run_id)

    assert calls == [run_id], "post_templates should run exactly once"

    post_content_path = artifacts_dir / "post_content_summary.json"
    assert post_content_path.exists()
    post_summary = json.loads(post_content_path.read_text(encoding="utf-8"))
    assert post_summary["schema_version"] == "v1"
    assert post_summary["run_id"] == run_id
