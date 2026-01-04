from __future__ import annotations

import json
import sys
from pathlib import Path

from tests.helpers import write_metadata, write_post_templates

sys.path.insert(0, str(Path(__file__).parent.parent))
import orchestrator  # noqa: E402


def _write_video_render_summary(base_dir: Path, run_id: str) -> None:
    summary_path = (
        base_dir / "output" / run_id / "artifacts" / "video_render_summary.json"
    )
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary = {"hook": "Hook line", "cta": "Call to action"}
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def test_orchestrator_auto_publish_request_after_dispatch(tmp_path, monkeypatch):
    run_id = "run_publish_auto"
    write_post_templates(tmp_path)
    write_metadata(tmp_path, run_id, platform="youtube_community")
    _write_video_render_summary(tmp_path, run_id)

    pipeline_path = tmp_path / "pipeline.yml"
    pipeline_path.write_text(
        """pipeline: publish_request_auto
steps:
  - id: post_templates
    uses: post_templates
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(orchestrator, "ROOT", tmp_path)
    monkeypatch.setenv("PIPELINE_ENABLED", "true")

    orchestrator.run_pipeline(pipeline_path, run_id)

    publish_path = tmp_path / "output" / run_id / "artifacts" / "publish_request.json"
    assert publish_path.exists()
    payload = json.loads(publish_path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "v1"
    assert payload["engine"] == "publish_request_v0"
    assert payload["inputs"]["dispatch_audit"].startswith(f"output/{run_id}/")
    assert payload["inputs"]["post_content_summary"].startswith(f"output/{run_id}/")


def test_orchestrator_explicit_publish_request_runs_once(tmp_path, monkeypatch):
    run_id = "run_publish_explicit"
    write_post_templates(tmp_path)
    write_metadata(tmp_path, run_id, platform="youtube")
    _write_video_render_summary(tmp_path, run_id)

    pipeline_path = tmp_path / "pipeline.yml"
    pipeline_path.write_text(
        """pipeline: publish_request_explicit
steps:
  - id: post_templates
    uses: post_templates
  - id: dispatch
    uses: dispatch.v0
  - id: publish_request
    uses: publish_request.v0
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(orchestrator, "ROOT", tmp_path)
    monkeypatch.setenv("PIPELINE_ENABLED", "true")

    calls = {"count": 0}
    original_generate = orchestrator.publish_request_v0.generate_publish_request

    def wrapped_generate(*args, **kwargs):
        calls["count"] += 1
        return original_generate(*args, **kwargs)

    monkeypatch.setattr(
        orchestrator.publish_request_v0, "generate_publish_request", wrapped_generate
    )

    orchestrator.run_pipeline(pipeline_path, run_id)

    assert calls["count"] == 1
    publish_path = tmp_path / "output" / run_id / "artifacts" / "publish_request.json"
    assert publish_path.exists()
