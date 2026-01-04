from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from automation_core.publish_request_v0 import (
    generate_publish_request,
    validate_publish_request,
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


def _write_dispatch_audit(
    base_dir: Path,
    run_id: str,
    *,
    platform: str = "youtube",
    target: str | None = None,
    short: str = "short content",
    long: str = "long content",
) -> Path:
    path = base_dir / "output" / run_id / "artifacts" / "dispatch_audit.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    inputs = {
        "post_content_summary": f"output/{run_id}/artifacts/post_content_summary.json",
        "dispatch_enabled": False,
        "dispatch_mode": "dry_run",
        "platform": platform,
    }
    if target is not None:
        inputs["target"] = target
    audit = {
        "schema_version": "v1",
        "engine": "dispatch_v0",
        "run_id": run_id,
        "checked_at": "2026-01-01T00:00:00Z",
        "inputs": inputs,
        "result": {
            "status": "skipped",
            "message": "Dispatch disabled (DISPATCH_ENABLED=false or unset)",
            "actions": [
                {
                    "type": "print",
                    "label": "short",
                    "bytes": len(short.encode("utf-8")),
                },
                {
                    "type": "print",
                    "label": "long",
                    "bytes": len(long.encode("utf-8")),
                },
                {
                    "type": "noop",
                    "label": "publish",
                    "reason": "dispatch disabled",
                },
            ],
        },
        "errors": [],
    }
    path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _expected_idempotency_key(
    *, run_id: str, target: str, platform: str, content_long: str
) -> str:
    content_hash = hashlib.sha256(content_long.encode("utf-8")).hexdigest()
    raw = f"{run_id}|{target}|{platform}|{content_hash}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def test_generate_publish_request_happy_path(tmp_path, monkeypatch):
    run_id = "run_publish"
    short = "short content"
    long = "long content"
    _write_post_summary(tmp_path, run_id, platform="youtube", short=short, long=long)
    _write_dispatch_audit(
        tmp_path, run_id, platform="youtube", target="youtube_community"
    )
    monkeypatch.setenv("PIPELINE_ENABLED", "true")

    payload, path = generate_publish_request(run_id, base_dir=tmp_path)

    assert path is not None
    assert path.exists()
    validated = validate_publish_request(payload, run_id)
    assert validated["inputs"]["platform"] == "youtube"
    assert validated["inputs"]["target"] == "youtube_community"
    assert validated["request"]["content_short"] == short
    assert validated["request"]["content_long"] == long
    assert validated["request"]["attachments"] == []
    assert validated["inputs"]["post_content_summary"].startswith("output/")
    assert validated["inputs"]["dispatch_audit"].startswith("output/")
    expected_key = _expected_idempotency_key(
        run_id=run_id,
        target="youtube_community",
        platform="youtube",
        content_long=long,
    )
    assert validated["controls"]["idempotency_key"] == expected_key


def test_target_fallback_to_platform(tmp_path, monkeypatch):
    run_id = "run_fallback"
    _write_post_summary(tmp_path, run_id, platform="youtube_community")
    _write_dispatch_audit(tmp_path, run_id, platform="youtube_community", target=None)
    monkeypatch.setenv("PIPELINE_ENABLED", "true")

    payload, _ = generate_publish_request(run_id, base_dir=tmp_path)

    assert payload["inputs"]["target"] == "youtube_community"


def test_kill_switch_blocks_write(tmp_path, monkeypatch):
    run_id = "run_disabled"
    monkeypatch.setenv("PIPELINE_ENABLED", "false")

    payload, path = generate_publish_request(run_id, base_dir=tmp_path)

    assert payload == {}
    assert path is None
    assert not (
        tmp_path / "output" / run_id / "artifacts" / "publish_request.json"
    ).exists()


def test_idempotency_deterministic(tmp_path, monkeypatch):
    run_id = "run_idem"
    _write_post_summary(tmp_path, run_id, short="hello", long="world")
    _write_dispatch_audit(tmp_path, run_id, target="youtube")
    monkeypatch.setenv("PIPELINE_ENABLED", "true")

    payload1, _ = generate_publish_request(run_id, base_dir=tmp_path)
    payload2, _ = generate_publish_request(run_id, base_dir=tmp_path)

    assert (
        payload1["controls"]["idempotency_key"]
        == payload2["controls"]["idempotency_key"]
    )


def test_missing_dispatch_audit_raises(tmp_path, monkeypatch):
    run_id = "run_missing"
    _write_post_summary(tmp_path, run_id)
    monkeypatch.setenv("PIPELINE_ENABLED", "true")

    with pytest.raises(FileNotFoundError):
        generate_publish_request(run_id, base_dir=tmp_path)
    assert not (
        tmp_path / "output" / run_id / "artifacts" / "publish_request.json"
    ).exists()
