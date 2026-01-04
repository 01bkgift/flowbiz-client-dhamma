from __future__ import annotations

import json
from pathlib import Path

import pytest

from automation_core.dispatch_v0 import (
    MAX_PREVIEW_CHARS,
    _validate_run_id,
    cli_main,
    generate_dispatch_audit,
    parse_dispatch_enabled,
    validate_dispatch_audit,
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


def test_validate_dispatch_audit_happy_path(tmp_path, monkeypatch):
    run_id = "run_validate_audit"
    _write_post_summary(tmp_path, run_id)
    monkeypatch.setenv("PIPELINE_ENABLED", "true")

    audit, _ = generate_dispatch_audit(run_id, base_dir=tmp_path)

    validated = validate_dispatch_audit(audit, run_id)
    actions = validated["result"]["actions"]
    assert [a["label"] for a in actions] == ["short", "long", "publish"]
    assert actions[0]["bytes"] == len("short content")
    assert actions[2]["type"] == "noop"


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


def test_dispatch_dry_run_enabled(tmp_path, monkeypatch):
    run_id = "run_dry"
    _write_post_summary(tmp_path, run_id, platform="youtube_community")
    monkeypatch.setenv("PIPELINE_ENABLED", "true")
    monkeypatch.setenv("DISPATCH_ENABLED", "true")

    audit, _ = generate_dispatch_audit(run_id, base_dir=tmp_path)

    assert audit["result"]["status"] == "dry_run"
    assert audit["inputs"]["dispatch_enabled"] is True
    assert audit["inputs"]["target"] == "youtube_community"
    assert audit["result"]["actions"][-1]["reason"] == "dry_run default"


def test_dispatch_target_env_override(tmp_path, monkeypatch):
    run_id = "run_target"
    _write_post_summary(tmp_path, run_id, platform="youtube_community")
    monkeypatch.setenv("PIPELINE_ENABLED", "true")
    monkeypatch.setenv("DISPATCH_ENABLED", "true")
    monkeypatch.setenv("DISPATCH_TARGET", "line")

    audit, _ = generate_dispatch_audit(run_id, base_dir=tmp_path)

    assert audit["inputs"]["target"] == "line"


def test_dispatch_print_only_mode(tmp_path, monkeypatch):
    run_id = "run_print_only"
    _write_post_summary(tmp_path, run_id)
    monkeypatch.setenv("PIPELINE_ENABLED", "true")
    monkeypatch.setenv("DISPATCH_ENABLED", "true")
    monkeypatch.setenv("DISPATCH_MODE", "print_only")

    audit, _ = generate_dispatch_audit(run_id, base_dir=tmp_path)

    assert audit["result"]["status"] == "printed"
    assert audit["result"]["message"].startswith("Printed content only")


def test_dispatch_missing_post_summary_raises(tmp_path, monkeypatch):
    run_id = "run_missing"
    monkeypatch.setenv("PIPELINE_ENABLED", "true")

    with pytest.raises(FileNotFoundError):
        generate_dispatch_audit(run_id, base_dir=tmp_path)
    audit_path = tmp_path / "output" / run_id / "artifacts" / "dispatch_audit.json"
    assert audit_path.exists()
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    assert audit["result"]["status"] == "failed"
    assert audit["errors"]


def test_dispatch_mode_invalid_fails_and_writes_failed_audit(tmp_path, monkeypatch):
    run_id = "run_invalid_mode"
    _write_post_summary(tmp_path, run_id)
    monkeypatch.setenv("PIPELINE_ENABLED", "true")
    monkeypatch.setenv("DISPATCH_ENABLED", "true")
    monkeypatch.setenv("DISPATCH_MODE", "publish")

    with pytest.raises(ValueError, match="DISPATCH_MODE"):
        generate_dispatch_audit(run_id, base_dir=tmp_path)
    audit_path = tmp_path / "output" / run_id / "artifacts" / "dispatch_audit.json"
    assert audit_path.exists()
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    assert audit["result"]["status"] == "failed"
    assert audit["errors"]


@pytest.mark.parametrize(
    "bad_run_id",
    ["../escape", "/abs/path", "nested/path"],
)
def test_validate_run_id_invalid(bad_run_id):
    with pytest.raises(ValueError):
        _validate_run_id(bad_run_id)


def test_validate_post_content_summary_other_errors():
    base = {
        "schema_version": "v1",
        "engine": "post_templates",
        "run_id": "good",
        "inputs": {"platform": "youtube"},
        "outputs": {"short": "a", "long": "b"},
    }

    wrong_engine = base | {"engine": "other"}
    with pytest.raises(ValueError, match="engine"):
        validate_post_content_summary(wrong_engine, "good")

    wrong_run = base | {"run_id": "bad"}
    with pytest.raises(ValueError, match="run_id"):
        validate_post_content_summary(wrong_run, "good")

    missing_platform = base | {"inputs": {"platform": ""}}
    with pytest.raises(ValueError, match="platform"):
        validate_post_content_summary(missing_platform, "good")

    bad_outputs = base | {"outputs": {"short": 1, "long": "b"}}
    with pytest.raises(ValueError, match="outputs.short"):
        validate_post_content_summary(bad_outputs, "good")


def test_actions_are_deterministic(tmp_path, monkeypatch):
    run_id = "run_actions_det"
    _write_post_summary(tmp_path, run_id, short="hello", long="world")
    monkeypatch.setenv("PIPELINE_ENABLED", "true")

    audit1, _ = generate_dispatch_audit(run_id, base_dir=tmp_path)
    audit2, _ = generate_dispatch_audit(run_id, base_dir=tmp_path)

    assert audit1["result"]["actions"] == audit2["result"]["actions"]
