from __future__ import annotations

from typing import Any

from automation_core.contracts.publish_request_v1 import validate_publish_request

from .base import AdapterError, AdapterPreview
from .registry import AdapterRegistry

MAX_PREVIEW_CHARS = 500
PUBLISH_REASON = "no_publish_in_v0"


def build_bounded_preview(text: str, limit: int = MAX_PREVIEW_CHARS) -> str:
    if len(text) <= limit:
        return text
    return text[:limit]


def _safe_str(value: object) -> str:
    return value if isinstance(value, str) else ""


def _extract_target_platform(publish_request: object) -> tuple[str, str]:
    if not isinstance(publish_request, dict):
        return "", ""
    inputs = publish_request.get("inputs")
    if not isinstance(inputs, dict):
        return "", ""
    return _safe_str(inputs.get("target")), _safe_str(inputs.get("platform"))


def _build_empty_actions() -> list[dict[str, Any]]:
    return [
        {"type": "print", "label": "short", "bytes": 0, "preview": ""},
        {"type": "print", "label": "long", "bytes": 0, "preview": ""},
        {"type": "noop", "label": "publish", "reason": PUBLISH_REASON},
    ]


def _error_preview(
    *, target: str, platform: str, error: AdapterError
) -> AdapterPreview:
    return {
        "target": target,
        "platform": platform,
        "mode": "dry_run",
        "actions": _build_empty_actions(),
        "errors": [
            {
                "code": error.code,
                "message": error.message,
                "detail": error.detail,
                "step": "adapter.preview",
            }
        ],
    }


def _raise_invalid_preview(message: str, *, detail: object | None = None) -> None:
    raise AdapterError(code="invalid_preview", message=message, detail=detail)


def _validate_actions(actions: list[dict[str, Any]]) -> None:
    if len(actions) != 3:
        _raise_invalid_preview("actions must have 3 items")

    def require_print(action: dict[str, Any], label: str) -> None:
        if action.get("type") != "print" or action.get("label") != label:
            _raise_invalid_preview(f"action {label} must be print/{label}")
        bytes_value = action.get("bytes")
        if not isinstance(bytes_value, int) or bytes_value < 0:
            _raise_invalid_preview(f"action {label} bytes must be >= 0")
        preview = action.get("preview")
        if not isinstance(preview, str):
            _raise_invalid_preview(f"action {label} preview must be string")
        if len(preview) > MAX_PREVIEW_CHARS:
            _raise_invalid_preview(f"action {label} preview too long")

    def require_publish(action: dict[str, Any]) -> None:
        if action.get("type") != "noop" or action.get("label") != "publish":
            _raise_invalid_preview("action publish must be noop/publish")
        if action.get("reason") != PUBLISH_REASON:
            _raise_invalid_preview("action publish reason must be no_publish_in_v0")

    require_print(actions[0], "short")
    require_print(actions[1], "long")
    require_publish(actions[2])


def _validate_preview(
    preview: AdapterPreview, *, expected_target: str, expected_platform: str
) -> None:
    if not isinstance(preview, dict):
        _raise_invalid_preview("preview must be a dict")
    if preview.get("target") != expected_target:
        _raise_invalid_preview("target mismatch")
    if preview.get("platform") != expected_platform:
        _raise_invalid_preview("platform mismatch")
    if preview.get("mode") != "dry_run":
        _raise_invalid_preview("mode must be dry_run")
    errors = preview.get("errors")
    if not isinstance(errors, list):
        _raise_invalid_preview("errors must be a list")
    if errors:
        _raise_invalid_preview("errors must be empty on success")
    actions = preview.get("actions")
    if not isinstance(actions, list):
        _raise_invalid_preview("actions must be a list")
    _validate_actions(actions)


def preview_from_publish_request(
    publish_request: dict[str, Any], *, registry: AdapterRegistry
) -> AdapterPreview:
    target, platform = _extract_target_platform(publish_request)
    run_id_value = publish_request.get("run_id")
    run_id = run_id_value if isinstance(run_id_value, str) else ""
    try:
        validate_publish_request(publish_request, run_id)
    except Exception as exc:
        error = AdapterError(
            code="invalid_publish_request",
            message=f"invalid_publish_request: {exc}",
            detail={"error": str(exc)},
        )
        return _error_preview(target=target, platform=platform, error=error)

    try:
        adapter = registry.get(target)
        adapter.validate(publish_request)
        preview = adapter.build_preview(publish_request)
        _validate_preview(preview, expected_target=target, expected_platform=platform)
        return preview
    except AdapterError as exc:
        return _error_preview(target=target, platform=platform, error=exc)
    except Exception as exc:
        error = AdapterError(
            code="adapter_failure",
            message=f"adapter_failure: {exc}",
            detail={"error": str(exc)},
        )
        return _error_preview(target=target, platform=platform, error=error)
