from __future__ import annotations

from automation_core.adapters.noop import NoopAdapter
from automation_core.adapters.preview import (
    MAX_PREVIEW_CHARS,
    preview_from_publish_request,
)
from automation_core.adapters.registry import AdapterRegistry, get_default_registry
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


def test_preview_happy_path_returns_bounded_actions():
    long_text = "x" * 600
    payload = _make_publish_request(long=long_text)
    registry = AdapterRegistry()
    registry.register(NoopAdapter("youtube"))

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


def test_preview_end_to_end_with_default_registry_success():
    long_text = "x" * (MAX_PREVIEW_CHARS + 50)
    payload = _make_publish_request(
        target="youtube_community",
        platform="youtube",
        long=long_text,
    )
    registry = get_default_registry()

    preview = preview_from_publish_request(payload, registry=registry)

    assert preview["errors"] == []
    assert preview["target"] == "youtube_community"
    assert preview["platform"] == "youtube"
    assert preview["mode"] == "dry_run"
    actions = preview["actions"]
    assert [(action["type"], action["label"]) for action in actions] == [
        ("print", "short"),
        ("print", "long"),
        ("noop", "publish"),
    ]
    assert actions[0]["bytes"] == len(
        payload["request"]["content_short"].encode("utf-8")
    )
    assert actions[0]["preview"] == payload["request"]["content_short"]
    assert actions[1]["bytes"] == len(long_text.encode("utf-8"))
    assert actions[1]["preview"] == long_text[:MAX_PREVIEW_CHARS]
    assert actions[2]["reason"] == "no_publish_in_v0"


def test_preview_unknown_target_returns_structured_error():
    # NOTE: "tiktok" is intentionally not in ALLOWED_TARGETS_V0; verify safe errors.
    payload = _make_publish_request(target="tiktok")
    registry = get_default_registry()

    preview = preview_from_publish_request(payload, registry=registry)

    assert preview["errors"] == [
        {
            "code": "unknown_target",
            "message": "unknown_target: target=tiktok",
            "detail": None,
            "step": "adapter.preview",
        }
    ]
    actions = preview["actions"]
    assert [(action["type"], action["label"]) for action in actions] == [
        ("print", "short"),
        ("print", "long"),
        ("noop", "publish"),
    ]
    assert actions[0]["bytes"] == 0
    assert actions[0]["preview"] == ""
    assert actions[1]["bytes"] == 0
    assert actions[1]["preview"] == ""
    assert actions[2]["reason"] == "no_publish_in_v0"
