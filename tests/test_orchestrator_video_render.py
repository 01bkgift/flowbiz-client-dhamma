from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock

from automation_core.voiceover_tts import compute_input_sha256
from tests.helpers import write_metadata, write_post_templates

sys.path.insert(0, str(Path(__file__).parent.parent))
import orchestrator


def _snapshot_paths(root: Path) -> list[str]:
    return sorted(p.relative_to(root).as_posix() for p in root.rglob("*"))


def _write_voiceover_summary(
    root: Path, run_id: str, slug: str, sha12: str
) -> tuple[Path, str]:
    artifacts_dir = root / "output" / run_id / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    wav_rel = f"data/voiceovers/{run_id}/{slug}_{sha12}.wav"
    wav_path = root / wav_rel
    wav_path.parent.mkdir(parents=True, exist_ok=True)
    wav_path.write_bytes(b"RIFF")

    summary = {
        "schema_version": "v1",
        "run_id": run_id,
        "slug": slug,
        "text_sha256_12": sha12,
        "wav_path": wav_rel,
        "metadata_path": f"data/voiceovers/{run_id}/{slug}_{sha12}.json",
        "engine": "null_tts",
    }
    summary_path = artifacts_dir / "voiceover_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary_path, wav_rel


def test_orchestrator_video_render_kill_switch_no_side_effects(
    tmp_path, monkeypatch, capsys
):
    pipeline_path = tmp_path / "pipeline.yml"
    pipeline_path.write_text(
        """pipeline: video_render_kill_switch
steps:
  - id: video_render
    uses: video.render
    config:
      slug: demo
      dry_run: false
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(orchestrator, "ROOT", tmp_path)
    monkeypatch.setenv("PIPELINE_ENABLED", "false")
    mock_run = Mock()
    monkeypatch.setattr(orchestrator.subprocess, "run", mock_run)
    monkeypatch.setattr(
        "sys.argv",
        [
            "orchestrator.py",
            "--pipeline",
            str(pipeline_path),
            "--run-id",
            "run_kill",
        ],
    )

    before = _snapshot_paths(tmp_path)
    exit_code = orchestrator.main()
    after = _snapshot_paths(tmp_path)

    assert exit_code == 0
    assert before == after
    assert not (tmp_path / "output" / "run_kill").exists()
    assert not (tmp_path / "data" / "voiceovers").exists()
    assert mock_run.call_count == 0

    captured = capsys.readouterr()
    assert "Pipeline disabled by PIPELINE_ENABLED=false" in captured.out


def test_orchestrator_video_render_dry_run_no_writes(tmp_path, monkeypatch):
    run_id = "run_dry"
    slug = "dryrender"
    sha12 = compute_input_sha256("Hello dry run")[:12]
    _, wav_rel = _write_voiceover_summary(tmp_path, run_id, slug, sha12)

    pipeline_path = tmp_path / "pipeline.yml"
    pipeline_path.write_text(
        f"""pipeline: video_render_dry_run
steps:
  - id: video_render
    uses: video.render
    config:
      slug: {slug}
      dry_run: true
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(orchestrator, "ROOT", tmp_path)
    monkeypatch.setenv("PIPELINE_ENABLED", "true")
    mock_run = Mock()
    monkeypatch.setattr(orchestrator.subprocess, "run", mock_run)

    before = _snapshot_paths(tmp_path)
    summary = orchestrator.run_pipeline(pipeline_path, run_id)
    after = _snapshot_paths(tmp_path)

    assert before == after
    assert mock_run.call_count == 0

    result = summary["results"]["video_render"]
    planned = result["planned_paths"]
    for key in (
        "summary_path",
        "output_mp4_path",
        "input_voiceover_summary",
        "input_wav_path",
    ):
        assert not Path(planned[key]).is_absolute()

    assert (
        planned["summary_path"]
        == f"output/{run_id}/artifacts/video_render_summary.json"
    )
    assert (
        planned["input_voiceover_summary"]
        == f"output/{run_id}/artifacts/voiceover_summary.json"
    )
    assert planned["input_wav_path"] == wav_rel
    assert planned["output_mp4_path"] == f"output/{run_id}/artifacts/{slug}_{sha12}.mp4"


def test_orchestrator_video_render_real_run_writes_summary(tmp_path, monkeypatch):
    run_id = "run_real"
    slug = "realrender"
    sha12 = compute_input_sha256("Hello real run")[:12]
    _, wav_rel = _write_voiceover_summary(tmp_path, run_id, slug, sha12)
    write_post_templates(tmp_path)
    write_metadata(
        tmp_path,
        run_id,
        title="Test Video Title",
        description="Test video description",
        tags=["#test", "#video"],
    )

    pipeline_path = tmp_path / "pipeline.yml"
    pipeline_path.write_text(
        f"""pipeline: video_render_real_run
steps:
  - id: video_render
    uses: video.render
    config:
      slug: {slug}
      dry_run: false
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(orchestrator, "ROOT", tmp_path)
    monkeypatch.setenv("PIPELINE_ENABLED", "true")

    def fake_run(cmd, check, capture_output, text):
        return subprocess.CompletedProcess(cmd, 0, stdout="ok", stderr="")

    monkeypatch.setattr(orchestrator.subprocess, "run", fake_run)

    orchestrator.run_pipeline(pipeline_path, run_id)

    summary_path = (
        tmp_path / "output" / run_id / "artifacts" / "video_render_summary.json"
    )
    assert summary_path.exists()

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["schema_version"] == "v1"
    assert summary["run_id"] == run_id
    assert summary["slug"] == slug
    assert summary["text_sha256_12"] == sha12
    assert (
        summary["input_voiceover_summary"]
        == f"output/{run_id}/artifacts/voiceover_summary.json"
    )
    assert summary["input_wav_path"] == wav_rel
    assert summary["output_mp4_path"] == f"output/{run_id}/artifacts/{slug}_{sha12}.mp4"
    assert summary["engine"] == "ffmpeg"
    assert isinstance(summary["ffmpeg_cmd"], list)

    for key in ("input_voiceover_summary", "input_wav_path", "output_mp4_path"):
        assert not Path(summary[key]).is_absolute()
    for arg in summary["ffmpeg_cmd"]:
        assert not Path(arg).is_absolute()

    assert wav_rel in summary["ffmpeg_cmd"]
    assert summary["output_mp4_path"] in summary["ffmpeg_cmd"]

    # Verify post_templates was auto-invoked after video_render
    post_content_path = (
        tmp_path / "output" / run_id / "artifacts" / "post_content_summary.json"
    )
    assert post_content_path.exists(), (
        "post_content_summary.json should be created by auto-invocation "
        "of post_templates after video_render completes"
    )
    post_summary = json.loads(post_content_path.read_text(encoding="utf-8"))
    assert post_summary["schema_version"] == "v1"
    assert post_summary["run_id"] == run_id


def test_orchestrator_video_render_voiceover_summary_traversal_blocked(
    tmp_path, monkeypatch
):
    pipeline_path = tmp_path / "pipeline.yml"
    pipeline_path.write_text(
        """pipeline: video_render_traversal
steps:
  - id: video_render
    uses: video.render
    config:
      slug: traversal
      voiceover_summary_path: ../secrets.json
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(orchestrator, "ROOT", tmp_path)
    monkeypatch.setenv("PIPELINE_ENABLED", "true")

    try:
        orchestrator.run_pipeline(pipeline_path, "run_traversal")
    except ValueError as exc:
        assert "voiceover_summary_path" in str(exc)
    else:
        raise AssertionError("Expected ValueError for voiceover_summary_path traversal")


def test_orchestrator_video_render_image_path_traversal_blocked(tmp_path, monkeypatch):
    pipeline_path = tmp_path / "pipeline.yml"
    pipeline_path.write_text(
        """pipeline: video_render_image_traversal
steps:
  - id: video_render
    uses: video.render
    config:
      slug: traversal
      image_path: ../image.png
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(orchestrator, "ROOT", tmp_path)
    monkeypatch.setenv("PIPELINE_ENABLED", "true")

    try:
        orchestrator.run_pipeline(pipeline_path, "run_traversal")
    except ValueError as exc:
        assert "image_path" in str(exc)
    else:
        raise AssertionError("Expected ValueError for image_path traversal")


def test_orchestrator_video_render_missing_voiceover_summary_has_clear_error(
    tmp_path, monkeypatch
):
    pipeline_path = tmp_path / "pipeline.yml"
    pipeline_path.write_text(
        """pipeline: video_render_missing_summary
steps:
  - id: video_render
    uses: video.render
    config:
      slug: demo
      dry_run: true
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(orchestrator, "ROOT", tmp_path)
    monkeypatch.setenv("PIPELINE_ENABLED", "true")

    try:
        orchestrator.run_pipeline(pipeline_path, "run_missing")
    except FileNotFoundError as exc:
        assert "Voiceover summary not found" in str(exc)
        assert "output/run_missing/artifacts/voiceover_summary.json" in str(exc)
    else:
        raise AssertionError("Expected FileNotFoundError for missing voiceover summary")


def test_orchestrator_video_render_missing_image_has_clear_error(tmp_path, monkeypatch):
    run_id = "run_img_missing"
    slug = "imgmissing"
    sha12 = compute_input_sha256("Hello image missing")[:12]
    _write_voiceover_summary(tmp_path, run_id, slug, sha12)

    pipeline_path = tmp_path / "pipeline.yml"
    pipeline_path.write_text(
        f"""pipeline: video_render_missing_image
steps:
  - id: video_render
    uses: video.render
    config:
      slug: {slug}
      image_path: thumbnails/does_not_exist.png
      dry_run: true
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(orchestrator, "ROOT", tmp_path)
    monkeypatch.setenv("PIPELINE_ENABLED", "true")

    try:
        orchestrator.run_pipeline(pipeline_path, run_id)
    except FileNotFoundError as exc:
        assert "Image input not found" in str(exc)
        assert "thumbnails/does_not_exist.png" in str(exc)
    else:
        raise AssertionError("Expected FileNotFoundError for missing image")
