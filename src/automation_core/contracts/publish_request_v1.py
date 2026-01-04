from __future__ import annotations

from typing import Any

from automation_core.contracts.common import (
    _hash_text,
    _validate_relative_path,
    _validate_run_id,
)

ENGINE_NAME = "publish_request_v0"


def _compute_idempotency_key(
    *, run_id: str, target: str, platform: str, content_long: str
) -> str:
    content_hash = _hash_text(content_long)
    raw = f"{run_id}|{target}|{platform}|{content_hash}"
    return _hash_text(raw)


def validate_publish_request(payload: dict[str, Any], run_id: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("publish_request must be an object")
    if payload.get("schema_version") != "v1":
        raise ValueError("publish_request.schema_version must be 'v1'")
    if payload.get("engine") != ENGINE_NAME:
        raise ValueError(f"publish_request.engine must be '{ENGINE_NAME}'")

    _validate_run_id(run_id)
    payload_run_id = payload.get("run_id")
    if not isinstance(payload_run_id, str):
        raise ValueError("publish_request.run_id must be a string")
    _validate_run_id(payload_run_id)
    if payload_run_id != run_id:
        raise ValueError("publish_request.run_id must match run_id")

    checked_at = payload.get("checked_at")
    if not isinstance(checked_at, str) or not checked_at.strip():
        raise ValueError("publish_request.checked_at is required")

    inputs = payload.get("inputs")
    if not isinstance(inputs, dict):
        raise ValueError("publish_request.inputs must be an object")
    summary_path = inputs.get("post_content_summary")
    dispatch_path = inputs.get("dispatch_audit")
    _validate_relative_path(summary_path, "inputs.post_content_summary")
    _validate_relative_path(dispatch_path, "inputs.dispatch_audit")
    platform = inputs.get("platform")
    if not isinstance(platform, str) or not platform.strip():
        raise ValueError("inputs.platform is required")
    target = inputs.get("target")
    if not isinstance(target, str) or not target.strip():
        raise ValueError("inputs.target is required")

    request = payload.get("request")
    if not isinstance(request, dict):
        raise ValueError("publish_request.request must be an object")
    content_short = request.get("content_short")
    if not isinstance(content_short, str):
        raise ValueError("request.content_short must be a string")
    content_long = request.get("content_long")
    if not isinstance(content_long, str):
        raise ValueError("request.content_long must be a string")
    attachments = request.get("attachments")
    if not isinstance(attachments, list):
        raise ValueError("request.attachments must be a list")
    if attachments:
        raise ValueError("request.attachments must be empty in v1")

    controls = payload.get("controls")
    if not isinstance(controls, dict):
        raise ValueError("publish_request.controls must be an object")
    dry_run = controls.get("dry_run")
    if dry_run is not True:
        raise ValueError("controls.dry_run must be true")
    allow_publish = controls.get("allow_publish")
    if allow_publish is not False:
        raise ValueError("controls.allow_publish must be false")
    idempotency_key = controls.get("idempotency_key")
    if not isinstance(idempotency_key, str) or not idempotency_key.strip():
        raise ValueError("controls.idempotency_key is required")
    if len(idempotency_key) != 64 or any(
        ch not in "0123456789abcdef" for ch in idempotency_key.lower()
    ):
        raise ValueError("controls.idempotency_key must be 64 hex chars")
    expected_key = _compute_idempotency_key(
        run_id=run_id,
        target=target,
        platform=platform,
        content_long=content_long,
    )
    if idempotency_key != expected_key:
        raise ValueError("controls.idempotency_key must be deterministic")

    policy = payload.get("policy")
    if not isinstance(policy, dict):
        raise ValueError("publish_request.policy must be an object")
    if policy.get("status") != "pending":
        raise ValueError("policy.status must be 'pending'")
    reasons = policy.get("reasons")
    if not isinstance(reasons, list):
        raise ValueError("policy.reasons must be a list")

    errors = payload.get("errors")
    if errors is None:
        errors = []
    if not isinstance(errors, list):
        raise ValueError("errors must be a list")
    for error in errors:
        if not isinstance(error, dict):
            raise ValueError("each error must be an object")
    return payload
