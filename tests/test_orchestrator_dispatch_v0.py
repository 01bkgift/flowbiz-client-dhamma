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


def test_orchestrator_runs_dispatch_after_post_templates(tmp_path, monkeypatch):
    run_id = "run_dispatch"
    write_post_templates(tmp_path)
    write_metadata(
        tmp_path,
        run_id,
        title="Dispatch title",
        description="Dispatch description",
        tags=["#dispatch"],
        platform="youtube_community",
    )
    _write_video_render_summary(tmp_path, run_id)

    pipeline_path = tmp_path / "pipeline.yml"
    pipeline_path.write_text(
        """pipeline: dispatch_auto
steps:
  - id: post_templates
    uses: post_templates
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(orchestrator, "ROOT", tmp_path)
    monkeypatch.setenv("PIPELINE_ENABLED", "true")
    monkeypatch.delenv("DISPATCH_ENABLED", raising=False)

    orchestrator.run_pipeline(pipeline_path, run_id)

    audit_path = tmp_path / "output" / run_id / "artifacts" / "dispatch_audit.json"
    assert audit_path.exists()
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    assert audit["schema_version"] == "v1"
    assert audit["engine"] == "dispatch_v0"
    assert audit["inputs"]["post_content_summary"].startswith(f"output/{run_id}/")


def test_orchestrator_dispatch_respects_kill_switch(tmp_path, monkeypatch, capsys):
    run_id = "run_dispatch_disabled"
    pipeline_path = tmp_path / "pipeline.yml"
    pipeline_path.write_text(
        """pipeline: dispatch_disabled
steps:
  - id: post_templates
    uses: post_templates
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(orchestrator, "ROOT", tmp_path)
    monkeypatch.setenv("PIPELINE_ENABLED", "false")
    monkeypatch.setattr(
        "sys.argv",
        [
            "orchestrator.py",
            "--pipeline",
            str(pipeline_path),
            "--run-id",
            run_id,
        ],
    )

    exit_code = orchestrator.main()

    assert exit_code == 0
    assert not (tmp_path / "output" / run_id).exists()
    captured = capsys.readouterr()
    assert "Pipeline disabled" in captured.out
