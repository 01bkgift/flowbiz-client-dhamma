from __future__ import annotations

import json
from pathlib import Path

from automation_core.voiceover_tts import compute_input_sha256


def _snapshot_paths(root: Path) -> list[str]:
    return sorted(p.relative_to(root).as_posix() for p in root.rglob("*"))


def test_orchestrator_voiceover_tts_kill_switch_no_side_effects(
    tmp_path, monkeypatch, capsys
):
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent))
    import orchestrator

    slug = "demo"
    script_path = tmp_path / "scripts" / "voiceover.txt"
    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text("Hello world", encoding="utf-8")
    pipeline_path = tmp_path / "pipeline.yml"
    pipeline_path.write_text(
        f"""pipeline: voiceover_tts_kill_switch
steps:
  - id: voiceover_step
    uses: voiceover.tts
    config:
      slug: {slug}
      script_path: scripts/voiceover.txt
      dry_run: false
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
            "run_kill_switch",
        ],
    )

    before = _snapshot_paths(tmp_path)
    exit_code = orchestrator.main()
    after = _snapshot_paths(tmp_path)

    assert exit_code == 0
    assert before == after
    assert not (tmp_path / "output" / "run_kill_switch").exists()
    assert not (tmp_path / "data" / "voiceovers").exists()

    captured = capsys.readouterr()
    assert "Pipeline disabled by PIPELINE_ENABLED=false" in captured.out


def test_orchestrator_voiceover_tts_dry_run_no_writes(tmp_path, monkeypatch):
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent))
    import orchestrator

    slug = "dryrun"
    script_text = "Line one\nLine two\n"
    script_path = tmp_path / "scripts" / "voiceover.txt"
    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text(script_text, encoding="utf-8")
    pipeline_path = tmp_path / "pipeline.yml"
    pipeline_path.write_text(
        f"""pipeline: voiceover_tts_dry_run
steps:
  - id: voiceover_step
    uses: voiceover.tts
    config:
      slug: {slug}
      script_path: scripts/voiceover.txt
      dry_run: true
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(orchestrator, "ROOT", tmp_path)
    monkeypatch.setenv("PIPELINE_ENABLED", "true")

    before = _snapshot_paths(tmp_path)
    summary = orchestrator.run_pipeline(pipeline_path, "run_dry")
    after = _snapshot_paths(tmp_path)

    assert before == after
    assert not (tmp_path / "output" / "run_dry").exists()
    assert not (tmp_path / "data" / "voiceovers").exists()

    result = summary["results"]["voiceover_step"]
    planned = result["planned_paths"]
    for key in ("summary_path", "wav_path", "metadata_path"):
        assert not Path(planned[key]).is_absolute()
    assert planned["summary_path"] == "output/run_dry/artifacts/voiceover_summary.json"

    sha = compute_input_sha256(script_text)
    assert planned["wav_path"].startswith("data/voiceovers/run_dry/")
    assert planned["wav_path"].endswith(f"{slug}_{sha[:12]}.wav")
    assert planned["metadata_path"].startswith("data/voiceovers/run_dry/")
    assert planned["metadata_path"].endswith(f"{slug}_{sha[:12]}.json")


def test_orchestrator_voiceover_tts_real_run_creates_artifacts(tmp_path, monkeypatch):
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent))
    import orchestrator

    slug = "realrun"
    script_text = "Hello voiceover\nSecond line\n"
    script_path = tmp_path / "scripts" / "voiceover.txt"
    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text(script_text, encoding="utf-8")

    pipeline_path = tmp_path / "pipeline.yml"
    pipeline_path.write_text(
        f"""pipeline: voiceover_tts_real_run
steps:
  - id: voiceover_step
    uses: voiceover.tts
    config:
      slug: {slug}
      script_path: scripts/voiceover.txt
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(orchestrator, "ROOT", tmp_path)
    monkeypatch.setenv("PIPELINE_ENABLED", "true")

    orchestrator.run_pipeline(pipeline_path, "run_real")

    summary_path = (
        tmp_path / "output" / "run_real" / "artifacts" / "voiceover_summary.json"
    )
    assert summary_path.exists()

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["schema_version"] == "v1"
    assert summary["run_id"] == "run_real"
    assert summary["slug"] == slug
    assert isinstance(summary["text_sha256_12"], str)
    assert len(summary["text_sha256_12"]) == 12
    assert isinstance(summary["engine"], str)
    assert summary["engine"]

    for key in ("wav_path", "metadata_path"):
        assert not Path(summary[key]).is_absolute()

    sha = compute_input_sha256(script_text)
    assert summary["wav_path"].startswith("data/voiceovers/run_real/")
    assert summary["wav_path"].endswith(f"{slug}_{sha[:12]}.wav")
    assert summary["metadata_path"].startswith("data/voiceovers/run_real/")
    assert summary["metadata_path"].endswith(f"{slug}_{sha[:12]}.json")

    wav_path = tmp_path / summary["wav_path"]
    metadata_path = tmp_path / summary["metadata_path"]
    assert wav_path.exists()
    assert metadata_path.exists()


def test_orchestrator_voiceover_tts_script_path_traversal_blocked(
    tmp_path, monkeypatch
):
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent))
    import orchestrator

    pipeline_path = tmp_path / "pipeline.yml"
    pipeline_path.write_text(
        """pipeline: voiceover_tts_traversal
steps:
  - id: voiceover_step
    uses: voiceover.tts
    config:
      slug: traversal
      script_path: ../secrets.txt
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(orchestrator, "ROOT", tmp_path)
    monkeypatch.setenv("PIPELINE_ENABLED", "true")

    try:
        orchestrator.run_pipeline(pipeline_path, "run_traversal")
    except ValueError as exc:
        assert "script_path" in str(exc)
    else:
        raise AssertionError("Expected ValueError for script_path traversal")
