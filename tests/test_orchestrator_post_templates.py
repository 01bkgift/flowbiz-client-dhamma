from __future__ import annotations

import json
import sys
from pathlib import Path

from tests.helpers import write_metadata, write_post_templates

sys.path.insert(0, str(Path(__file__).parent.parent))
import orchestrator


def _write_video_render_summary(base_dir: Path, run_id: str) -> None:
    """เขียน video_render_summary.json สำหรับการทดสอบ"""
    summary_path = (
        base_dir / "output" / run_id / "artifacts" / "video_render_summary.json"
    )
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary = {"hook": "Hook line", "cta": "Call to action"}
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _assert_relative(value: str) -> None:
    """
    ตรวจสอบว่า path เป็น relative path และไม่มี path traversal

    Args:
        value: ค่า path ในรูปแบบสตริงที่ต้องการตรวจสอบ

    Returns:
        None
    """
    path = Path(value)
    assert not path.is_absolute()
    assert ".." not in path.parts


def test_orchestrator_post_templates_enabled(tmp_path, monkeypatch):
    run_id = "run_post_templates"
    write_post_templates(tmp_path)
    write_metadata(
        tmp_path,
        run_id,
        title="Sample title",
        description="Sample summary",
        tags=["#alpha", "#beta"],
    )
    _write_video_render_summary(tmp_path, run_id)

    pipeline_path = tmp_path / "pipeline.yml"
    pipeline_path.write_text(
        """pipeline: post_templates_enabled
steps:
  - id: post_templates
    uses: post_templates
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(orchestrator, "ROOT", tmp_path)
    monkeypatch.setenv("PIPELINE_ENABLED", "true")
    monkeypatch.delenv("PIPELINE_PARAMS_JSON", raising=False)

    orchestrator.run_pipeline(pipeline_path, run_id)

    summary_path = (
        tmp_path / "output" / run_id / "artifacts" / "post_content_summary.json"
    )
    assert summary_path.exists()

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["schema_version"] == "v1"

    inputs = summary["inputs"]
    _assert_relative(inputs["template_short"])
    _assert_relative(inputs["template_long"])

    sources = inputs["sources"]
    assert sources == [
        f"output/{run_id}/metadata.json",
        f"output/{run_id}/artifacts/video_render_summary.json",
    ]
    for source in sources:
        _assert_relative(source)


def test_orchestrator_post_templates_disabled_no_output(tmp_path, monkeypatch, capsys):
    run_id = "run_post_templates_disabled"
    pipeline_path = tmp_path / "pipeline.yml"
    pipeline_path.write_text(
        """pipeline: post_templates_disabled
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
    assert "Pipeline disabled by PIPELINE_ENABLED=false" in captured.out
