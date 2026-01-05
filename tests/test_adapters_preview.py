from __future__ import annotations

import hashlib
from typing import Any

from automation_core.adapters.base import AdapterPreview
from automation_core.adapters.preview import (
    build_bounded_preview,
    preview_from_publish_request,
)
from automation_core.adapters.registry import AdapterRegistry


def _expected_idempotency_key(
    *, run_id: str, target: str, platform: str, content_long: str
) -> str:
    content_hash = hashlib.sha256(content_long.encode("utf-8")).hexdigest()
    raw = f"{run_id}|{target}|{platform}|{content_hash}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _make_publish_request(
    *,
    run_id: str = "run_preview",
    target: str = "youtube",
    platform: str = "youtube",
    short: str = "short content",
    long: str = "long content",
) -> dict:
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


class PreviewAdapter:
    def __init__(self, target: str) -> None:
        self._target = target

    def target(self) -> str:
        return self._target

    def validate(self, publish_request: dict[str, Any]) -> None:
        pass

    def build_preview(self, publish_request: dict[str, Any]) -> AdapterPreview:
        short_text = publish_request["request"]["content_short"]
        long_text = publish_request["request"]["content_long"]
        return {
            "target": publish_request["inputs"]["target"],
            "platform": publish_request["inputs"]["platform"],
            "mode": "dry_run",
            "actions": [
                {
                    "type": "print",
                    "label": "short",
                    "bytes": len(short_text.encode("utf-8")),
                    "preview": build_bounded_preview(short_text),
                },
                {
                    "type": "print",
                    "label": "long",
                    "bytes": len(long_text.encode("utf-8")),
                    "preview": build_bounded_preview(long_text),
                },
                {"type": "noop", "label": "publish", "reason": "no_publish_in_v0"},
            ],
            "errors": [],
        }


def test_preview_happy_path_returns_bounded_actions():
    long_text = "x" * 600
    payload = _make_publish_request(long=long_text)
    registry = AdapterRegistry()
    registry.register(PreviewAdapter("youtube"))

    preview = preview_from_publish_request(payload, registry=registry)

    actions = preview["actions"]
    assert preview["mode"] == "dry_run"
    assert preview["errors"] == []
    assert [(action["type"], action["label"]) for action in actions] == [
        ("print", "short"),
        ("print", "long"),
        ("noop", "publish"),
    ]
    assert actions[0]["bytes"] == len(
        payload["request"]["content_short"].encode("utf-8")
    )
    assert actions[1]["bytes"] == len(long_text.encode("utf-8"))
    assert len(actions[1]["preview"]) == 500
    assert actions[2]["reason"] == "no_publish_in_v0"


def test_preview_invalid_publish_request_returns_error_preview():
    payload = _make_publish_request()
    payload["schema_version"] = "v0"
    registry = AdapterRegistry()

    preview = preview_from_publish_request(payload, registry=registry)

    assert preview["errors"]
    assert preview["errors"][0]["code"] == "invalid_publish_request"
    assert preview["actions"][0]["bytes"] == 0
    assert preview["actions"][0]["preview"] == ""
    assert preview["actions"][1]["bytes"] == 0
    assert preview["actions"][1]["preview"] == ""
    assert preview["actions"][2]["reason"] == "no_publish_in_v0"


def test_preview_unknown_target_returns_error_preview():
    payload = _make_publish_request(target="facebook")
    registry = AdapterRegistry()

    preview = preview_from_publish_request(payload, registry=registry)

    assert preview["errors"]
    assert preview["errors"][0]["code"] == "unknown_target"
    assert preview["actions"][2]["reason"] == "no_publish_in_v0"
