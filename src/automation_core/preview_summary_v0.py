from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from automation_core.adapters import get_default_registry, preview_from_publish_request
from automation_core.contracts.common import (
    _artifact_rel_path,
    _validate_relative_path,
    _validate_run_id,
)
from automation_core.contracts.publish_request_v1 import validate_publish_request

REPO_ROOT = Path(__file__).resolve().parents[2]
ENGINE_NAME = "preview_summary_v0"
PREVIEW_SUMMARY_NAME = "preview_summary.json"
PUBLISH_REQUEST_NAME = "publish_request.json"
POST_SUMMARY_NAME = "post_content_summary.json"
DISPATCH_AUDIT_NAME = "dispatch_audit.json"
MAX_PREVIEW_CHARS = 500
PUBLISH_REASON = "no_publish_in_v0"


def parse_pipeline_enabled(env_value: str | None) -> bool:
    if env_value is None:
        return True
    return env_value.strip().lower() not in ("false", "0", "no", "off", "disabled")


def _publish_request_rel_path(run_id: str, *, validate: bool = True) -> str:
    if validate:
        run_id = _validate_run_id(run_id)
    return _artifact_rel_path(run_id, PUBLISH_REQUEST_NAME, validate=False)


def _validate_errors(errors: list[dict[str, Any]]) -> None:
    for error in errors:
        if not isinstance(error, dict):
            raise ValueError("each error must be an object")
        code = error.get("code")
        if not isinstance(code, str) or not code.strip():
            raise ValueError("error.code is required")
        message = error.get("message")
        if not isinstance(message, str) or not message.strip():
            raise ValueError("error.message is required")
        if error.get("step") != "adapter.preview":
            raise ValueError("error.step must be 'adapter.preview'")
        if "detail" not in error:
            raise ValueError("error.detail is required")


def _validate_actions(actions: list[dict[str, Any]]) -> None:
    if len(actions) != 3:
        raise ValueError("summary.actions must have 3 items")

    def require_print(action: dict[str, Any], label: str) -> None:
        if action.get("type") != "print" or action.get("label") != label:
            raise ValueError(f"summary.actions {label} must be print/{label}")
        bytes_value = action.get("bytes")
        if not isinstance(bytes_value, int) or bytes_value < 0:
            raise ValueError(f"summary.actions {label}.bytes must be >= 0")
        preview = action.get("preview")
        if not isinstance(preview, str):
            raise ValueError(f"summary.actions {label}.preview must be string")
        if len(preview) > MAX_PREVIEW_CHARS:
            raise ValueError(f"summary.actions {label}.preview too long")

    def require_publish(action: dict[str, Any]) -> None:
        if action.get("type") != "noop" or action.get("label") != "publish":
            raise ValueError("summary.actions publish must be noop/publish")
        if action.get("reason") != PUBLISH_REASON:
            raise ValueError("summary.actions publish reason must be no_publish_in_v0")

    require_print(actions[0], "short")
    require_print(actions[1], "long")
    require_publish(actions[2])


def _validate_preview(
    preview: dict[str, Any], *, expected_target: str, expected_platform: str
) -> None:
    if not isinstance(preview, dict):
        raise ValueError("preview must be an object")
    if preview.get("target") != expected_target:
        raise ValueError("preview.target must match inputs.target")
    if preview.get("platform") != expected_platform:
        raise ValueError("preview.platform must match inputs.platform")
    if preview.get("mode") != "dry_run":
        raise ValueError("preview.mode must be dry_run")
    errors = preview.get("errors")
    if not isinstance(errors, list):
        raise ValueError("preview.errors must be a list")
    _validate_errors(errors)
    actions = preview.get("actions")
    if not isinstance(actions, list):
        raise ValueError("preview.actions must be a list")
    _validate_actions(actions)


def load_publish_request(
    run_id: str, base_dir: Path = REPO_ROOT
) -> tuple[str, dict[str, Any]]:
    run_id = _validate_run_id(run_id)
    relative = _publish_request_rel_path(run_id, validate=False)
    path = base_dir / relative
    if not path.is_file():
        raise FileNotFoundError(f"Publish request not found: {relative}")
    raw = path.read_text(encoding="utf-8")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {relative}") from exc
    if not isinstance(data, dict):
        raise ValueError("publish_request must be a JSON object")
    validate_publish_request(data, run_id)
    return relative, data


def build_preview_summary(
    *,
    run_id: str,
    publish_request_path: str,
    publish_request: dict[str, Any],
    preview: dict[str, Any],
    checked_at: datetime | None = None,
) -> dict[str, Any]:
    checked = (checked_at or datetime.now(tz=UTC)).isoformat().replace("+00:00", "Z")
    inputs = publish_request["inputs"]
    post_summary = inputs["post_content_summary"]
    dispatch_audit = inputs["dispatch_audit"]
    platform = inputs["platform"]
    target = inputs["target"]
    summary_actions = [dict(action) for action in preview["actions"]]
    summary_errors = [dict(error) for error in preview["errors"]]
    payload = {
        "schema_version": "v1",
        "engine": ENGINE_NAME,
        "run_id": run_id,
        "checked_at": checked,
        "inputs": {
            "publish_request": publish_request_path,
            "post_content_summary": post_summary,
            "dispatch_audit": dispatch_audit,
            "platform": platform,
            "target": target,
        },
        "summary": {
            "target": preview["target"],
            "platform": preview["platform"],
            "mode": preview["mode"],
            "actions": summary_actions,
        },
        "policy": {
            "status": "preview_only",
            "reasons": [],
        },
        "errors": summary_errors,
    }
    return payload


def validate_preview_summary(payload: dict[str, Any], run_id: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("preview_summary must be an object")
    if payload.get("schema_version") != "v1":
        raise ValueError("preview_summary.schema_version must be 'v1'")
    if payload.get("engine") != ENGINE_NAME:
        raise ValueError(f"preview_summary.engine must be '{ENGINE_NAME}'")

    _validate_run_id(run_id)
    payload_run_id = payload.get("run_id")
    if not isinstance(payload_run_id, str):
        raise ValueError("preview_summary.run_id must be a string")
    _validate_run_id(payload_run_id)
    if payload_run_id != run_id:
        raise ValueError("preview_summary.run_id must match run_id")

    checked_at = payload.get("checked_at")
    if not isinstance(checked_at, str) or not checked_at.strip():
        raise ValueError("preview_summary.checked_at is required")

    inputs = payload.get("inputs")
    if not isinstance(inputs, dict):
        raise ValueError("preview_summary.inputs must be an object")
    publish_request = inputs.get("publish_request")
    publish_request = _validate_relative_path(publish_request, "inputs.publish_request")
    expected_publish_request = _publish_request_rel_path(run_id, validate=False)
    if publish_request != expected_publish_request:
        raise ValueError(
            "inputs.publish_request must be 'output/<run_id>/artifacts/publish_request.json'"
        )
    post_summary = _validate_relative_path(
        inputs.get("post_content_summary"), "inputs.post_content_summary"
    )
    expected_post_summary = _artifact_rel_path(
        run_id, POST_SUMMARY_NAME, validate=False
    )
    if post_summary != expected_post_summary:
        raise ValueError(
            "inputs.post_content_summary must be 'output/<run_id>/artifacts/post_content_summary.json'"
        )
    dispatch_audit = _validate_relative_path(
        inputs.get("dispatch_audit"), "inputs.dispatch_audit"
    )
    expected_dispatch_audit = _artifact_rel_path(
        run_id, DISPATCH_AUDIT_NAME, validate=False
    )
    if dispatch_audit != expected_dispatch_audit:
        raise ValueError(
            "inputs.dispatch_audit must be 'output/<run_id>/artifacts/dispatch_audit.json'"
        )
    platform = inputs.get("platform")
    if not isinstance(platform, str) or not platform.strip():
        raise ValueError("inputs.platform is required")
    target = inputs.get("target")
    if not isinstance(target, str) or not target.strip():
        raise ValueError("inputs.target is required")

    summary = payload.get("summary")
    if not isinstance(summary, dict):
        raise ValueError("preview_summary.summary must be an object")
    if summary.get("target") != target:
        raise ValueError("summary.target must match inputs.target")
    if summary.get("platform") != platform:
        raise ValueError("summary.platform must match inputs.platform")
    if summary.get("mode") != "dry_run":
        raise ValueError("summary.mode must be dry_run")
    actions = summary.get("actions")
    if not isinstance(actions, list):
        raise ValueError("summary.actions must be a list")
    _validate_actions(actions)

    policy = payload.get("policy")
    if not isinstance(policy, dict):
        raise ValueError("preview_summary.policy must be an object")
    if policy.get("status") != "preview_only":
        raise ValueError("policy.status must be 'preview_only'")
    reasons = policy.get("reasons")
    if not isinstance(reasons, list):
        raise ValueError("policy.reasons must be a list")
    for reason in reasons:
        if not isinstance(reason, str):
            raise ValueError("policy.reasons must be a list of strings")

    errors = payload.get("errors") or []
    if not isinstance(errors, list):
        raise ValueError("errors must be a list")
    _validate_errors(errors)
    return payload


def generate_preview_summary(
    run_id: str,
    *,
    base_dir: Path = REPO_ROOT,
    checked_at: datetime | None = None,
) -> tuple[dict[str, Any], Path | None]:
    run_id = _validate_run_id(run_id)
    if not parse_pipeline_enabled(os.environ.get("PIPELINE_ENABLED")):
        print("Pipeline disabled by PIPELINE_ENABLED=false")
        return {}, None

    publish_rel, publish_request = load_publish_request(run_id, base_dir)
    inputs = publish_request["inputs"]
    target = inputs["target"]
    platform = inputs["platform"]
    preview = preview_from_publish_request(
        publish_request, registry=get_default_registry()
    )
    _validate_preview(preview, expected_target=target, expected_platform=platform)
    payload = build_preview_summary(
        run_id=run_id,
        publish_request_path=publish_rel,
        publish_request=publish_request,
        preview=preview,
        checked_at=checked_at,
    )
    validate_preview_summary(payload, run_id)

    output_path = base_dir / "output" / run_id / "artifacts" / PREVIEW_SUMMARY_NAME
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), "utf-8")
    output_rel = output_path.relative_to(base_dir).as_posix()
    print(f"Preview summary v0: wrote {output_rel}")
    return payload, output_path


def cli_main(argv: list[str] | None = None, base_dir: Path | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Preview summary v0 - build preview_summary.json"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    summary_parser = subparsers.add_parser(
        "preview_summary", help="Generate preview summary (v0)"
    )
    summary_parser.add_argument("--run-id", required=True, help="Run identifier")

    args = parser.parse_args(argv)
    base_dir = base_dir or REPO_ROOT

    try:
        if args.command == "preview_summary":
            generate_preview_summary(args.run_id, base_dir=base_dir)
    except Exception as exc:  # pragma: no cover - surfaces CLI errors
        print(f"Error: {exc}")
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(cli_main())
