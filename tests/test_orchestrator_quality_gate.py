from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).parent.parent))
import orchestrator


def _write_video_render_summary(root: Path, run_id: str, output_mp4_rel: str) -> Path:
    artifacts_dir = root / "output" / run_id / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "schema_version": "v1",
        "run_id": run_id,
        "output_mp4_path": output_mp4_rel,
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


def test_orchestrator_quality_gate_missing_mp4_fails(tmp_path, monkeypatch):
    run_id = "run_missing"
    output_mp4_rel = f"output/{run_id}/artifacts/missing.mp4"
    _write_video_render_summary(tmp_path, run_id, output_mp4_rel)

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
