from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).parent.parent))
import orchestrator


def _write_quality_gate_summary(
    root: Path, run_id: str, decision: str, output_mp4_rel: str
) -> Path:
    artifacts_dir = root / "output" / run_id / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "schema_version": "v1",
        "run_id": run_id,
        "output_mp4_path": output_mp4_rel,
        "decision": decision,
    }
    summary_path = artifacts_dir / "quality_gate_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary_path


def _write_mp4(root: Path, output_mp4_rel: str, content: bytes = b"fake mp4") -> Path:
    mp4_path = root / output_mp4_rel
    mp4_path.parent.mkdir(parents=True, exist_ok=True)
    mp4_path.write_bytes(content)
    return mp4_path


def _write_pipeline(root: Path) -> Path:
    pipeline_path = root / "pipeline.yml"
    pipeline_path.write_text(
        """pipeline: youtube_upload_test
steps:
  - id: youtube_upload
    uses: youtube.upload
""",
        encoding="utf-8",
    )
    return pipeline_path


def test_orchestrator_youtube_upload_skipped_when_disabled(tmp_path, monkeypatch):
    run_id = "run_disabled"
    output_mp4_rel = f"output/{run_id}/artifacts/demo.mp4"
    _write_mp4(tmp_path, output_mp4_rel)
    _write_quality_gate_summary(tmp_path, run_id, "pass", output_mp4_rel)
    pipeline_path = _write_pipeline(tmp_path)

    monkeypatch.setattr(orchestrator, "ROOT", tmp_path)
    monkeypatch.setenv("PIPELINE_ENABLED", "true")
    monkeypatch.delenv("YOUTUBE_UPLOAD_ENABLED", raising=False)

    mock_upload = Mock()
    monkeypatch.setattr(orchestrator.youtube_upload, "upload_video", mock_upload)

    orchestrator.run_pipeline(pipeline_path, run_id)

    summary_path = (
        tmp_path / "output" / run_id / "artifacts" / "youtube_upload_summary.json"
    )
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["decision"] == "skipped"
    assert summary["error"]["code"] == "upload_disabled"
    assert summary["attempt_count"] == 0
    assert mock_upload.call_count == 0


def test_orchestrator_youtube_upload_skipped_when_disabled_without_quality_summary(
    tmp_path, monkeypatch
):
    run_id = "run_disabled_no_quality"
    pipeline_path = _write_pipeline(tmp_path)

    monkeypatch.setattr(orchestrator, "ROOT", tmp_path)
    monkeypatch.setenv("PIPELINE_ENABLED", "true")
    monkeypatch.delenv("YOUTUBE_UPLOAD_ENABLED", raising=False)

    mock_upload = Mock()
    monkeypatch.setattr(orchestrator.youtube_upload, "upload_video", mock_upload)

    orchestrator.run_pipeline(pipeline_path, run_id)

    summary_path = (
        tmp_path / "output" / run_id / "artifacts" / "youtube_upload_summary.json"
    )
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["decision"] == "skipped"
    assert summary["error"]["code"] == "upload_disabled"
    assert summary["attempt_count"] == 0
    assert mock_upload.call_count == 0


def test_orchestrator_youtube_upload_skipped_when_quality_fail(tmp_path, monkeypatch):
    run_id = "run_quality_fail"
    output_mp4_rel = f"output/{run_id}/artifacts/demo.mp4"
    _write_mp4(tmp_path, output_mp4_rel)
    _write_quality_gate_summary(tmp_path, run_id, "fail", output_mp4_rel)
    pipeline_path = _write_pipeline(tmp_path)

    monkeypatch.setattr(orchestrator, "ROOT", tmp_path)
    monkeypatch.setenv("PIPELINE_ENABLED", "true")
    monkeypatch.setenv("YOUTUBE_UPLOAD_ENABLED", "true")

    mock_upload = Mock()
    monkeypatch.setattr(orchestrator.youtube_upload, "upload_video", mock_upload)

    orchestrator.run_pipeline(pipeline_path, run_id)

    summary_path = (
        tmp_path / "output" / run_id / "artifacts" / "youtube_upload_summary.json"
    )
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["decision"] == "skipped"
    assert summary["error"]["code"] == "quality_gate_not_pass"
    assert summary["attempt_count"] == 0
    assert mock_upload.call_count == 0


def test_orchestrator_youtube_upload_uploaded_success(tmp_path, monkeypatch):
    run_id = "run_success"
    output_mp4_rel = f"output/{run_id}/artifacts/demo.mp4"
    _write_mp4(tmp_path, output_mp4_rel)
    _write_quality_gate_summary(tmp_path, run_id, "pass", output_mp4_rel)
    pipeline_path = _write_pipeline(tmp_path)

    monkeypatch.setattr(orchestrator, "ROOT", tmp_path)
    monkeypatch.setenv("PIPELINE_ENABLED", "true")
    monkeypatch.setenv("YOUTUBE_UPLOAD_ENABLED", "true")

    mock_upload = Mock(return_value="abc123")
    monkeypatch.setattr(orchestrator.youtube_upload, "upload_video", mock_upload)

    orchestrator.run_pipeline(pipeline_path, run_id)

    summary_path = (
        tmp_path / "output" / run_id / "artifacts" / "youtube_upload_summary.json"
    )
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["decision"] == "uploaded"
    assert summary["video_id"] == "abc123"
    assert summary["video_url"] == "https://www.youtube.com/watch?v=abc123"
    assert summary["attempt_count"] == 1


def test_orchestrator_youtube_upload_retry_then_success(tmp_path, monkeypatch):
    class RetryableError(Exception):
        def __init__(self, status: int):
            super().__init__("retryable")
            self.status = status

    run_id = "run_retry"
    output_mp4_rel = f"output/{run_id}/artifacts/demo.mp4"
    _write_mp4(tmp_path, output_mp4_rel)
    _write_quality_gate_summary(tmp_path, run_id, "pass", output_mp4_rel)
    pipeline_path = _write_pipeline(tmp_path)

    monkeypatch.setattr(orchestrator, "ROOT", tmp_path)
    monkeypatch.setenv("PIPELINE_ENABLED", "true")
    monkeypatch.setenv("YOUTUBE_UPLOAD_ENABLED", "true")
    monkeypatch.setattr(orchestrator.time, "sleep", lambda _: None)

    calls = {"count": 0}

    def fake_upload(*_args, **_kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise RetryableError(status=429)
        return "abc123"

    monkeypatch.setattr(orchestrator.youtube_upload, "upload_video", fake_upload)

    orchestrator.run_pipeline(pipeline_path, run_id)

    summary_path = (
        tmp_path / "output" / run_id / "artifacts" / "youtube_upload_summary.json"
    )
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["decision"] == "uploaded"
    assert summary["attempt_count"] == 2


def test_orchestrator_youtube_upload_failed_after_retries(tmp_path, monkeypatch):
    class RetryableError(Exception):
        def __init__(self, status: int):
            super().__init__("retryable")
            self.status = status

    run_id = "run_failed"
    output_mp4_rel = f"output/{run_id}/artifacts/demo.mp4"
    _write_mp4(tmp_path, output_mp4_rel)
    _write_quality_gate_summary(tmp_path, run_id, "pass", output_mp4_rel)
    pipeline_path = _write_pipeline(tmp_path)

    monkeypatch.setattr(orchestrator, "ROOT", tmp_path)
    monkeypatch.setenv("PIPELINE_ENABLED", "true")
    monkeypatch.setenv("YOUTUBE_UPLOAD_ENABLED", "true")
    monkeypatch.setenv("YOUTUBE_UPLOAD_MAX_RETRIES", "2")
    monkeypatch.setattr(orchestrator.time, "sleep", lambda _: None)

    def fake_upload(*_args, **_kwargs):
        raise RetryableError(status=503)

    monkeypatch.setattr(orchestrator.youtube_upload, "upload_video", fake_upload)

    try:
        orchestrator.run_pipeline(pipeline_path, run_id)
    except RuntimeError as exc:
        assert "YouTube upload failed" in str(exc)
        assert "upload_failed_after_retries" in str(exc)
    else:
        raise AssertionError("Expected RuntimeError for upload retries exhaustion")

    summary_path = (
        tmp_path / "output" / run_id / "artifacts" / "youtube_upload_summary.json"
    )
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["decision"] == "failed"
    assert summary["error"]["code"] == "upload_failed_after_retries"
    assert summary["attempt_count"] == 3


def test_orchestrator_youtube_upload_failed_when_deps_missing(tmp_path, monkeypatch):
    run_id = "run_deps_missing"
    output_mp4_rel = f"output/{run_id}/artifacts/demo.mp4"
    _write_mp4(tmp_path, output_mp4_rel)
    _write_quality_gate_summary(tmp_path, run_id, "pass", output_mp4_rel)
    pipeline_path = _write_pipeline(tmp_path)

    monkeypatch.setattr(orchestrator, "ROOT", tmp_path)
    monkeypatch.setenv("PIPELINE_ENABLED", "true")
    monkeypatch.setenv("YOUTUBE_UPLOAD_ENABLED", "true")

    def fake_upload(*_args, **_kwargs):
        raise orchestrator.youtube_upload.YoutubeDepsMissingError("deps missing")

    monkeypatch.setattr(orchestrator.youtube_upload, "upload_video", fake_upload)

    try:
        orchestrator.run_pipeline(pipeline_path, run_id)
    except RuntimeError as exc:
        assert "youtube_deps_missing" in str(exc)
    else:
        raise AssertionError("Expected RuntimeError for deps missing")

    summary_path = (
        tmp_path / "output" / run_id / "artifacts" / "youtube_upload_summary.json"
    )
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["decision"] == "failed"
    assert summary["error"]["code"] == "youtube_deps_missing"
    assert summary["attempt_count"] == 1


def test_orchestrator_youtube_upload_failed_when_auth_missing(tmp_path, monkeypatch):
    run_id = "run_auth_missing"
    output_mp4_rel = f"output/{run_id}/artifacts/demo.mp4"
    _write_mp4(tmp_path, output_mp4_rel)
    _write_quality_gate_summary(tmp_path, run_id, "pass", output_mp4_rel)
    pipeline_path = _write_pipeline(tmp_path)

    monkeypatch.setattr(orchestrator, "ROOT", tmp_path)
    monkeypatch.setenv("PIPELINE_ENABLED", "true")
    monkeypatch.setenv("YOUTUBE_UPLOAD_ENABLED", "true")

    def fake_upload(*_args, **_kwargs):
        raise orchestrator.youtube_upload.YoutubeAuthMissingError("auth missing")

    monkeypatch.setattr(orchestrator.youtube_upload, "upload_video", fake_upload)

    try:
        orchestrator.run_pipeline(pipeline_path, run_id)
    except RuntimeError as exc:
        assert "auth_missing_env" in str(exc)
    else:
        raise AssertionError("Expected RuntimeError for auth missing")

    summary_path = (
        tmp_path / "output" / run_id / "artifacts" / "youtube_upload_summary.json"
    )
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["decision"] == "failed"
    assert summary["error"]["code"] == "auth_missing_env"
    assert summary["attempt_count"] == 1


def test_orchestrator_youtube_upload_failed_when_input_mp4_missing(
    tmp_path, monkeypatch
):
    run_id = "run_mp4_missing"
    output_mp4_rel = f"output/{run_id}/artifacts/missing.mp4"
    _write_quality_gate_summary(tmp_path, run_id, "pass", output_mp4_rel)
    pipeline_path = _write_pipeline(tmp_path)

    monkeypatch.setattr(orchestrator, "ROOT", tmp_path)
    monkeypatch.setenv("PIPELINE_ENABLED", "true")
    monkeypatch.setenv("YOUTUBE_UPLOAD_ENABLED", "true")

    mock_upload = Mock()
    monkeypatch.setattr(orchestrator.youtube_upload, "upload_video", mock_upload)

    try:
        orchestrator.run_pipeline(pipeline_path, run_id)
    except RuntimeError as exc:
        assert "input_mp4_missing" in str(exc)
    else:
        raise AssertionError("Expected RuntimeError for missing mp4")

    summary_path = (
        tmp_path / "output" / run_id / "artifacts" / "youtube_upload_summary.json"
    )
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["decision"] == "failed"
    assert summary["error"]["code"] == "input_mp4_missing"
    assert summary["attempt_count"] == 0
    assert mock_upload.call_count == 0
