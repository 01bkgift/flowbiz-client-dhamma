from __future__ import annotations

from pathlib import Path
from typing import Any

from automation_core.contracts.common import _validate_relative_path, _validate_run_id
from automation_core.contracts.post_content_summary_v1 import _post_summary_rel_path

ENGINE_NAME = "dispatch_v0"
ALLOWED_MODES = {"dry_run", "print_only"}


def validate_dispatch_audit(audit: dict[str, Any], run_id: str) -> dict[str, Any]:
    """Validate dispatch_audit payload (v1)."""
    if not isinstance(audit, dict):
        raise ValueError("dispatch_audit must be an object")
    if audit.get("schema_version") != "v1":
        raise ValueError("dispatch_audit.schema_version must be 'v1'")
    if audit.get("engine") != ENGINE_NAME:
        raise ValueError(f"dispatch_audit.engine must be '{ENGINE_NAME}'")

    _validate_run_id(run_id)
    audit_run_id = audit.get("run_id")
    if not isinstance(audit_run_id, str):
        raise ValueError("dispatch_audit.run_id must be a string")
    _validate_run_id(audit_run_id)
    if audit_run_id != run_id:
        raise ValueError("dispatch_audit.run_id must match run_id")

    checked_at = audit.get("checked_at")
    if not isinstance(checked_at, str) or not checked_at.strip():
        raise ValueError("dispatch_audit.checked_at is required")

    inputs = audit.get("inputs")
    if not isinstance(inputs, dict):
        raise ValueError("dispatch_audit.inputs must be an object")
    summary_path = inputs.get("post_content_summary")
    summary_path = _validate_relative_path(
        summary_path, "inputs.post_content_summary", check_root=False
    )
    summary_path_obj = Path(summary_path)

    expected_summary_path = _post_summary_rel_path(run_id)
    if summary_path_obj.as_posix() != expected_summary_path:
        raise ValueError(
            "inputs.post_content_summary must be 'output/<run_id>/artifacts/post_content_summary.json'"
        )
    dispatch_enabled = inputs.get("dispatch_enabled")
    if not isinstance(dispatch_enabled, bool):
        raise ValueError("inputs.dispatch_enabled must be a boolean")
    mode = inputs.get("dispatch_mode")
    if mode not in ALLOWED_MODES:
        raise ValueError("inputs.dispatch_mode must be one of: dry_run, print_only")
    target = inputs.get("target")
    if not isinstance(target, str) or not target.strip():
        raise ValueError("inputs.target is required")
    platform = inputs.get("platform")
    if not isinstance(platform, str) or not platform.strip():
        raise ValueError("inputs.platform is required")

    result = audit.get("result")
    if not isinstance(result, dict):
        raise ValueError("dispatch_audit.result must be an object")
    status = result.get("status")
    if status not in {"skipped", "dry_run", "printed", "failed"}:
        raise ValueError("result.status is invalid")
    message = result.get("message")
    if not isinstance(message, str) or not message.strip():
        raise ValueError("result.message is required")
    actions = result.get("actions")
    if not isinstance(actions, list) or len(actions) != 3:
        raise ValueError("result.actions must contain required entries")
    short_action, long_action, publish_action = actions
    if short_action.get("type") != "print" or short_action.get("label") != "short":
        raise ValueError("result.actions[0] must be print short")
    if not isinstance(short_action.get("bytes"), int) or short_action["bytes"] < 0:
        raise ValueError("result.actions[0].bytes must be non-negative int")
    if long_action.get("type") != "print" or long_action.get("label") != "long":
        raise ValueError("result.actions[1] must be print long")
    if not isinstance(long_action.get("bytes"), int) or long_action["bytes"] < 0:
        raise ValueError("result.actions[1].bytes must be non-negative int")
    if publish_action.get("type") != "noop" or publish_action.get("label") != "publish":
        raise ValueError("result.actions[2] must be noop publish")
    if (
        not isinstance(publish_action.get("reason"), str)
        or not publish_action["reason"]
    ):
        raise ValueError("result.actions[2].reason is required")

    errors = audit.get("errors")
    if errors is None:
        errors = []
    if not isinstance(errors, list):
        raise ValueError("errors must be a list")
    for err in errors:
        if not isinstance(err, dict):
            raise ValueError("each error must be an object")
        if not isinstance(err.get("code"), str) or not err["code"]:
            raise ValueError("error.code is required")
        if not isinstance(err.get("message"), str) or not err["message"]:
            raise ValueError("error.message is required")
        if err.get("step") != "dispatch.v0":
            raise ValueError("error.step must be 'dispatch.v0'")
        # detail is intentionally flexible; accept any type (including None)
    return audit


def _build_actions(
    short_bytes: int,
    long_bytes: int,
    publish_reason: str,
    *,
    target: str,
    adapter: str,
) -> list[dict[str, Any]]:
    short_b = max(0, short_bytes)
    long_b = max(0, long_bytes)
    return [
        {
            "type": "print",
            "label": "short",
            "bytes": short_b,
            "adapter": adapter,
            "target": target,
        },
        {
            "type": "print",
            "label": "long",
            "bytes": long_b,
            "adapter": adapter,
            "target": target,
        },
        {
            "type": "noop",
            "label": "publish",
            "reason": publish_reason,
            "adapter": adapter,
            "target": target,
        },
    ]
