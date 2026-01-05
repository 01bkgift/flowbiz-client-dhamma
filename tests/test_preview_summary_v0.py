from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from automation_core import preview_summary_v0
from automation_core.contracts import publish_request_v1


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
    target: str = "youtube_community",
    platform: str = "youtube",
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


def _write_publish_request(
    base_dir: Path, run_id: str, payload: dict[str, object]
) -> None:
    path = base_dir / "output" / run_id / "artifacts" / "publish_request.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_preview_summary_happy_path_writes_file(tmp_path):
    run_id = "run_preview_summary"
    long_text = "x" * 600
    payload = _make_publish_request(run_id=run_id, long=long_text)
    _write_publish_request(tmp_path, run_id, payload)

    checked_at = datetime(2026, 1, 1, tzinfo=UTC)
    summary, output_path = preview_summary_v0.generate_preview_summary(
        run_id, base_dir=tmp_path, checked_at=checked_at
    )

    assert output_path is not None
    assert output_path.is_file()
    data = json.loads(output_path.read_text(encoding="utf-8"))
    assert data == summary
    assert data["schema_version"] == "v1"
    assert data["engine"] == "preview_summary_v0"
    assert data["run_id"] == run_id
    assert data["checked_at"] == "2026-01-01T00:00:00Z"
    assert data["inputs"]["publish_request"] == (
        f"output/{run_id}/artifacts/publish_request.json"
    )
    assert (
        data["summary"]["actions"][0]["preview"] == payload["request"]["content_short"]
    )
    assert data["summary"]["actions"][1]["preview"] == long_text[:500]
    assert data["summary"]["mode"] == "dry_run"
    assert data["policy"]["status"] == "preview_only"
    assert data["errors"] == []


def test_preview_summary_kill_switch(tmp_path, monkeypatch):
    monkeypatch.setenv("PIPELINE_ENABLED", "false")
    summary, output_path = preview_summary_v0.generate_preview_summary(
        "run_preview_disabled", base_dir=tmp_path
    )

    assert summary == {}
    assert output_path is None
    assert not (
        tmp_path
        / "output"
        / "run_preview_disabled"
        / "artifacts"
        / "preview_summary.json"
    ).exists()


def test_preview_summary_deterministic_output(tmp_path):
    run_id = "run_preview_deterministic"
    payload = _make_publish_request(run_id=run_id, long="y" * 120)
    _write_publish_request(tmp_path, run_id, payload)
    checked_at = datetime(2026, 1, 1, tzinfo=UTC)

    first, _ = preview_summary_v0.generate_preview_summary(
        run_id, base_dir=tmp_path, checked_at=checked_at
    )
    second, _ = preview_summary_v0.generate_preview_summary(
        run_id, base_dir=tmp_path, checked_at=checked_at
    )

    assert first == second


def test_preview_summary_missing_publish_request(tmp_path):
    with pytest.raises(FileNotFoundError, match="Publish request not found"):
        preview_summary_v0.generate_preview_summary(
            "run_preview_missing", base_dir=tmp_path
        )


def test_preview_summary_schema_validation(tmp_path):
    run_id = "run_preview_schema"
    payload = _make_publish_request(run_id=run_id, long="schema check")
    _write_publish_request(tmp_path, run_id, payload)
    checked_at = datetime(2026, 1, 1, tzinfo=UTC)

    summary, _ = preview_summary_v0.generate_preview_summary(
        run_id, base_dir=tmp_path, checked_at=checked_at
    )
    summary["schema_version"] = "v0"

    with pytest.raises(ValueError, match="preview_summary.schema_version"):
        preview_summary_v0.validate_preview_summary(summary, run_id)
