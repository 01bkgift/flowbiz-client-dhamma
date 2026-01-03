from __future__ import annotations

import json
from pathlib import Path

import pytest

from automation_core.dispatch_v0 import (
    MAX_PREVIEW_CHARS,
    cli_main,
    generate_dispatch_audit,
    parse_dispatch_enabled,
    validate_post_content_summary,
)


def _write_post_summary(
    base_dir: Path,
    run_id: str,
    *,
    platform: str = "youtube",
    short: str = "short content",
    long: str = "long content",
) -> Path:
    path = base_dir / "output" / run_id / "artifacts" / "post_content_summary.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    summary = {
        "schema_version": "v1",
        "engine": "post_templates",
        "run_id": run_id,
        "checked_at": "2026-01-01T00:00:00Z",
        "inputs": {
            "lang": "th",
            "platform": platform,
            "template_short": "templates/post/short.md",
            "template_long": "templates/post/long.md",
            "sources": [],
        },
        "outputs": {"short": short, "long": long},
    }
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def test_parse_dispatch_enabled_truthy_values():
    assert parse_dispatch_enabled(None) is False
    assert parse_dispatch_enabled("true") is True
    assert parse_dispatch_enabled(" YES ") is True
    assert parse_dispatch_enabled("0") is False


def test_validate_post_content_summary_invalid_schema():
    payload = {
        "schema_version": "v2",
        "engine": "post_templates",
        "run_id": "run_x",
        "inputs": {"platform": "youtube"},
        "outputs": {"short": "a", "long": "b"},
    }
    with pytest.raises(ValueError, match="schema_version"):
        validate_post_content_summary(payload, "run_x")


def test_dispatch_audit_uses_relative_paths(tmp_path, monkeypatch):
    run_id = "run_rel"
    _write_post_summary(tmp_path, run_id, platform="youtube_community")
    monkeypatch.setenv("PIPELINE_ENABLED", "true")
    audit, audit_path = generate_dispatch_audit(run_id, base_dir=tmp_path)

    assert audit is not None
    assert audit["inputs"]["post_content_summary"].startswith("output/")
    assert not Path(audit["inputs"]["post_content_summary"]).is_absolute()
    assert audit_path is not None
    assert audit_path.relative_to(tmp_path)


def test_dispatch_prints_bounded_content(tmp_path, capsys, monkeypatch):
    run_id = "run_print"
    long_text = "a" * MAX_PREVIEW_CHARS + "TAIL_MARKER"
    _write_post_summary(tmp_path, run_id, short=long_text, long=long_text)
    monkeypatch.setenv("PIPELINE_ENABLED", "true")

    generate_dispatch_audit(run_id, base_dir=tmp_path)
    captured = capsys.readouterr().out

    assert long_text[:MAX_PREVIEW_CHARS] in captured
    assert "TAIL_MARKER" not in captured


def test_kill_switch_blocks_audit_write(tmp_path, monkeypatch):
    run_id = "run_disabled"
    _write_post_summary(tmp_path, run_id)
    monkeypatch.setenv("PIPELINE_ENABLED", "false")

    audit, audit_path = generate_dispatch_audit(run_id, base_dir=tmp_path)

    assert audit is None
    assert audit_path is None
    assert not (
        tmp_path / "output" / run_id / "artifacts" / "dispatch_audit.json"
    ).exists()


def test_cli_dispatch_creates_audit(tmp_path, monkeypatch):
    run_id = "run_cli"
    _write_post_summary(tmp_path, run_id)
    monkeypatch.setenv("PIPELINE_ENABLED", "true")

    exit_code = cli_main(["dispatch", "--run-id", run_id], base_dir=tmp_path)

    assert exit_code == 0
    assert (tmp_path / "output" / run_id / "artifacts" / "dispatch_audit.json").exists()
