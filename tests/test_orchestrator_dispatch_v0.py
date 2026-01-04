from __future__ import annotations

import json
import sys
from pathlib import Path

from tests.helpers import write_metadata, write_post_templates

sys.path.insert(0, str(Path(__file__).parent.parent))
import orchestrator  # noqa: E402


def _write_video_render_summary(
    base_dir: Path, run_id: str, *, output_mp4_path: str | None = None
) -> None:
    summary_path = (
        base_dir / "output" / run_id / "artifacts" / "video_render_summary.json"
    )
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary: dict[str, object] = {"hook": "Hook line", "cta": "Call to action"}
    if output_mp4_path:
        summary.update(
            {
                "schema_version": "v1",
                "run_id": run_id,
                "output_mp4_path": output_mp4_path,
                "platform": "youtube_community",
            }
        )
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
    monkeypatch.delenv("DISPATCH_ENABLED", raising=False)

    orchestrator.run_pipeline(pipeline_path, run_id)

    audit_path = tmp_path / "output" / run_id / "artifacts" / "dispatch_audit.json"
    assert audit_path.exists()
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    assert audit["schema_version"] == "v1"
    assert audit["engine"] == "dispatch_v0"
    assert audit["inputs"]["post_content_summary"].startswith(f"output/{run_id}/")


def test_orchestrator_auto_dispatch_after_quality_gate(tmp_path, monkeypatch):
    run_id = "run_quality_gate"
    write_post_templates(tmp_path)
    write_metadata(tmp_path, run_id, platform="youtube_community")

    output_mp4_rel = f"output/{run_id}/video.mp4"
    output_mp4_path = tmp_path / output_mp4_rel
    output_mp4_path.parent.mkdir(parents=True, exist_ok=True)
    output_mp4_path.write_bytes(b"fake mp4 data")

    _write_video_render_summary(tmp_path, run_id, output_mp4_path=output_mp4_rel)

    pipeline_path = tmp_path / "pipeline.yml"
    pipeline_path.write_text(
        """pipeline: dispatch_auto_quality_gate
steps:
  - id: quality_gate
    uses: quality.gate
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(orchestrator, "ROOT", tmp_path)
    monkeypatch.setenv("PIPELINE_ENABLED", "true")

    calls = {"count": 0}
    original_generate = orchestrator.dispatch_v0.generate_dispatch_audit

    def wrapped_generate(*args, **kwargs):
        calls["count"] += 1
        return original_generate(*args, **kwargs)

    monkeypatch.setattr(
        orchestrator.dispatch_v0, "generate_dispatch_audit", wrapped_generate
    )

    class _FakeCompleted:
        def __init__(self):
            self.returncode = 0
            self.stdout = json.dumps(
                {"format": {"duration": "1.0"}, "streams": [{"codec_type": "audio"}]}
            )

    def fake_run(*_args, **_kwargs):
        return _FakeCompleted()

    monkeypatch.setattr(orchestrator.subprocess, "run", fake_run)

    orchestrator.run_pipeline(pipeline_path, run_id)

    post_summary = (
        tmp_path / "output" / run_id / "artifacts" / "post_content_summary.json"
    )
    audit_path = tmp_path / "output" / run_id / "artifacts" / "dispatch_audit.json"
    assert post_summary.exists()
    assert audit_path.exists()
    assert calls["count"] == 1
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


def test_orchestrator_explicit_dispatch_runs_once(tmp_path, monkeypatch):
    run_id = "run_dispatch_explicit"
    write_post_templates(tmp_path)
    write_metadata(tmp_path, run_id, platform="youtube")
    _write_video_render_summary(tmp_path, run_id)

    pipeline_path = tmp_path / "pipeline.yml"
    pipeline_path.write_text(
        """pipeline: dispatch_explicit
steps:
  - id: post_templates
    uses: post_templates
  - id: dispatch
    uses: dispatch.v0
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(orchestrator, "ROOT", tmp_path)
    monkeypatch.setenv("PIPELINE_ENABLED", "true")

    calls: list[str] = []
    original = orchestrator.agent_dispatch_v0

    def wrapped(step, run_dir: Path):
        calls.append(run_dir.name)
        return original(step, run_dir)

    monkeypatch.setitem(orchestrator.AGENTS, "dispatch.v0", wrapped)

    orchestrator.run_pipeline(pipeline_path, run_id)

    assert calls == [run_id]
    audit_path = tmp_path / "output" / run_id / "artifacts" / "dispatch_audit.json"
    assert audit_path.exists()
