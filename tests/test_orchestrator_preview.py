from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from tests.helpers import write_metadata, write_post_templates

sys.path.insert(0, str(Path(__file__).parent.parent))
import orchestrator  # noqa: E402
from automation_core.contracts import publish_request_v1  # noqa: E402


def _write_video_render_summary(base_dir: Path, run_id: str) -> None:
    summary_path = (
        base_dir / "output" / run_id / "artifacts" / "video_render_summary.json"
    )
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary = {"hook": "Hook line", "cta": "Call to action"}
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _expected_idempotency_key(
    *, run_id: str, target: str, platform: str, content_long: str
) -> str:
    return publish_request_v1._compute_idempotency_key(
        run_id=run_id,
        target=target,
        platform=platform,
        content_long=content_long,
    )


def _make_publish_request(
    *,
    run_id: str,
    target: str,
    platform: str,
    short: str = "short content",
    long: str = "long content",
) -> dict[str, object]:
    return {
        "schema_version": "v1",
        "engine": "publish_request_v0",
        "run_id": run_id,
        "checked_at": "2026-01-01T00:00:00Z",
        "inputs": {
            "post_content_summary": f"output/{run_id}/artifacts/post_content_summary.json",
            "dispatch_audit": f"output/{run_id}/artifacts/dispatch_audit.json",
            "platform": platform,
            "target": target,
        },
        "request": {
            "content_short": short,
            "content_long": long,
            "attachments": [],
        },
        "controls": {
            "dry_run": True,
            "allow_publish": False,
            "idempotency_key": _expected_idempotency_key(
                run_id=run_id,
                target=target,
                platform=platform,
                content_long=long,
            ),
        },
        "policy": {"status": "pending", "reasons": []},
        "errors": [],
    }


def test_orchestrator_auto_preview_after_publish_request(tmp_path, monkeypatch):
    run_id = "run_preview_auto"
    write_post_templates(tmp_path)
    write_metadata(tmp_path, run_id, platform="youtube_community")
    _write_video_render_summary(tmp_path, run_id)

    pipeline_path = tmp_path / "pipeline.yml"
    pipeline_path.write_text(
        """pipeline: preview_auto
steps:
  - id: post_templates
    uses: post_templates
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(orchestrator, "ROOT", tmp_path)
    monkeypatch.setenv("PIPELINE_ENABLED", "true")

    calls = {"count": 0}
    original_preview = orchestrator.preview_from_publish_request

    def wrapped(payload, *, registry):
        calls["count"] += 1
        return original_preview(payload, registry=registry)

    monkeypatch.setattr(orchestrator, "preview_from_publish_request", wrapped)

    orchestrator.run_pipeline(pipeline_path, run_id)

    assert calls["count"] == 1


def test_orchestrator_explicit_preview_runs_once(tmp_path, monkeypatch):
    run_id = "run_preview_explicit"
    write_post_templates(tmp_path)
    write_metadata(tmp_path, run_id, platform="youtube_community")
    _write_video_render_summary(tmp_path, run_id)

    pipeline_path = tmp_path / "pipeline.yml"
    pipeline_path.write_text(
        """pipeline: preview_explicit
steps:
  - id: post_templates
    uses: post_templates
  - id: dispatch
    uses: dispatch.v0
  - id: publish_request
    uses: publish_request.v0
  - id: preview
    uses: preview
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(orchestrator, "ROOT", tmp_path)
    monkeypatch.setenv("PIPELINE_ENABLED", "true")

    calls = {"count": 0}
    original_preview = orchestrator.preview_from_publish_request

    def wrapped(payload, *, registry):
        calls["count"] += 1
        return original_preview(payload, registry=registry)

    monkeypatch.setattr(orchestrator, "preview_from_publish_request", wrapped)

    orchestrator.run_pipeline(pipeline_path, run_id)

    assert calls["count"] == 1


def test_orchestrator_preview_respects_kill_switch(tmp_path, monkeypatch, capsys):
    run_id = "run_preview_disabled"
    pipeline_path = tmp_path / "pipeline.yml"
    pipeline_path.write_text(
        """pipeline: preview_disabled
steps:
  - id: preview
    uses: preview
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(orchestrator, "ROOT", tmp_path)
    monkeypatch.setenv("PIPELINE_ENABLED", "false")

    calls = {"count": 0}
    original_preview = orchestrator.preview_from_publish_request

    def wrapped(payload, *, registry):
        calls["count"] += 1
        return original_preview(payload, registry=registry)

    monkeypatch.setattr(orchestrator, "preview_from_publish_request", wrapped)

    summary = orchestrator.run_pipeline(pipeline_path, run_id)

    captured = capsys.readouterr()
    assert summary["status"] == "disabled"
    assert calls["count"] == 0
    assert "Pipeline disabled by PIPELINE_ENABLED=false" in captured.out
    assert '"actions"' not in captured.out


def test_orchestrator_preview_unknown_target_propagates_structured_error(
    tmp_path, monkeypatch
):
    run_id = "run_preview_unknown"
    publish_path = tmp_path / "output" / run_id / "artifacts" / "publish_request.json"
    publish_path.parent.mkdir(parents=True, exist_ok=True)
    payload = _make_publish_request(run_id=run_id, target="tiktok", platform="youtube")
    publish_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    pipeline_path = tmp_path / "pipeline.yml"
    pipeline_path.write_text(
        """pipeline: preview_unknown
steps:
  - id: preview
    uses: preview
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(orchestrator, "ROOT", tmp_path)
    monkeypatch.setenv("PIPELINE_ENABLED", "true")

    with pytest.raises(orchestrator.PreviewError) as excinfo:
        orchestrator.run_pipeline(pipeline_path, run_id)

    preview = excinfo.value.preview
    assert preview["errors"] == [
        {
            "code": "unknown_target",
            "message": "unknown_target: target=tiktok",
            "detail": None,
            "step": "adapter.preview",
        }
    ]
