from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from automation_core.dispatch_v0 import (
    validate_dispatch_audit,
    validate_post_content_summary,
)
from automation_core.utils.env import parse_pipeline_enabled

REPO_ROOT = Path(__file__).resolve().parents[2]
ENGINE_NAME = "publish_request_v0"
POST_SUMMARY_NAME = "post_content_summary.json"
DISPATCH_AUDIT_NAME = "dispatch_audit.json"
PUBLISH_REQUEST_NAME = "publish_request.json"
MAX_PREVIEW_CHARS = 500


def _validate_run_id(run_id: str) -> str:
    """Ensure run_id is a single relative path segment."""
    path = Path(run_id)
    if not run_id or path.is_absolute() or path.drive or path.root:
        raise ValueError("run_id must be a relative path segment")
    if len(path.parts) != 1 or any(part in (".", "..") for part in path.parts):
        raise ValueError("run_id must not contain path separators or traversal")
    return run_id


def _bounded_preview(text: str, limit: int = MAX_PREVIEW_CHARS) -> str:
    if len(text) <= limit:
        return text
    return text[:limit]


def _validate_relative_path(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} is required")
    path = Path(value)
    if path.is_absolute() or path.drive or path.root or ".." in path.parts:
        raise ValueError(f"{label} must be relative without '..'")
    return value


def _artifact_rel_path(run_id: str, filename: str, *, validate: bool = True) -> str:
    if validate:
        run_id = _validate_run_id(run_id)
    return (Path("output") / run_id / "artifacts" / filename).as_posix()


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _compute_idempotency_key(
    *, run_id: str, target: str, platform: str, content_long: str
) -> str:
    content_hash = _hash_text(content_long)
    raw = f"{run_id}|{target}|{platform}|{content_hash}"
    return _hash_text(raw)


def load_post_content_summary(
    run_id: str, base_dir: Path = REPO_ROOT
) -> tuple[str, dict[str, Any]]:
    run_id = _validate_run_id(run_id)
    relative = _artifact_rel_path(run_id, POST_SUMMARY_NAME, validate=False)
    path = base_dir / relative
    raw = path.read_text(encoding="utf-8")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {relative}") from exc
    if not isinstance(data, dict):
        raise ValueError("post_content_summary must be a JSON object")
    validate_post_content_summary(data, run_id)
    return relative, data


def _normalize_dispatch_audit(
    audit: dict[str, Any], run_id: str
) -> tuple[dict[str, Any], str]:
    inputs = audit.get("inputs")
    if not isinstance(inputs, dict):
        raise ValueError("dispatch_audit.inputs must be an object")
    platform = inputs.get("platform")
    if not isinstance(platform, str) or not platform.strip():
        raise ValueError("dispatch_audit.inputs.platform is required")
    target_value = inputs.get("target")
    if not isinstance(target_value, str) or not target_value.strip():
        target = platform
        patched = audit.copy()
        patched_inputs = inputs.copy()
        patched_inputs["target"] = target
        patched["inputs"] = patched_inputs
        validate_dispatch_audit(patched, run_id)
        return patched, target
    validate_dispatch_audit(audit, run_id)
    return audit, target_value


def load_dispatch_audit(
    run_id: str, base_dir: Path = REPO_ROOT
) -> tuple[str, dict[str, Any], str]:
    run_id = _validate_run_id(run_id)
    relative = _artifact_rel_path(run_id, DISPATCH_AUDIT_NAME, validate=False)
    path = base_dir / relative
    raw = path.read_text(encoding="utf-8")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {relative}") from exc
    if not isinstance(data, dict):
        raise ValueError("dispatch_audit must be a JSON object")
    normalized, target = _normalize_dispatch_audit(data, run_id)
    return relative, normalized, target


def build_publish_request(
    *,
    run_id: str,
    post_content_summary: str,
    dispatch_audit: str,
    platform: str,
    target: str,
    content_short: str,
    content_long: str,
    checked_at: datetime | None = None,
) -> dict[str, Any]:
    checked = (checked_at or datetime.now(tz=UTC)).isoformat().replace("+00:00", "Z")
    idempotency_key = _compute_idempotency_key(
        run_id=run_id,
        target=target,
        platform=platform,
        content_long=content_long,
    )
    return {
        "schema_version": "v1",
        "engine": ENGINE_NAME,
        "run_id": run_id,
        "checked_at": checked,
        "inputs": {
            "post_content_summary": post_content_summary,
            "dispatch_audit": dispatch_audit,
            "platform": platform,
            "target": target,
        },
        "request": {
            "content_short": content_short,
            "content_long": content_long,
            "attachments": [],
        },
        "controls": {
            "dry_run": True,
            "allow_publish": False,
            "idempotency_key": idempotency_key,
        },
        "policy": {
            "status": "pending",
            "reasons": [],
        },
        "errors": [],
    }


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


def generate_publish_request(
    run_id: str,
    *,
    base_dir: Path = REPO_ROOT,
    checked_at: datetime | None = None,
) -> tuple[dict[str, Any], Path | None]:
    run_id = _validate_run_id(run_id)
    if not parse_pipeline_enabled(os.environ.get("PIPELINE_ENABLED")):
        print("Pipeline disabled by PIPELINE_ENABLED=false")
        return {}, None

    post_summary_rel, post_summary = load_post_content_summary(run_id, base_dir)
    dispatch_rel, _dispatch, target = load_dispatch_audit(run_id, base_dir)
    platform = str(post_summary["inputs"]["platform"])
    content_short = str(post_summary["outputs"]["short"])
    content_long = str(post_summary["outputs"]["long"])
    if not target:
        target = platform

    print(f"Publish request v0: start run_id={run_id}")
    print(f"Publish request v0: platform={platform} target={target}")
    print(f"Publish request v0: short bytes={len(content_short.encode('utf-8'))}")
    print(_bounded_preview(content_short))
    print(f"Publish request v0: long bytes={len(content_long.encode('utf-8'))}")
    print(_bounded_preview(content_long))

    payload = build_publish_request(
        run_id=run_id,
        post_content_summary=post_summary_rel,
        dispatch_audit=dispatch_rel,
        platform=platform,
        target=target,
        content_short=content_short,
        content_long=content_long,
        checked_at=checked_at,
    )
    validate_publish_request(payload, run_id)

    output_path = base_dir / "output" / run_id / "artifacts" / PUBLISH_REQUEST_NAME
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), "utf-8")
    output_rel = output_path.relative_to(base_dir).as_posix()
    print(f"Publish request v0: wrote {output_rel}")
    return payload, output_path


def cli_main(argv: list[str] | None = None, base_dir: Path | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Publish request v0 - build publish_request.json"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    request_parser = subparsers.add_parser(
        "publish_request", help="Generate publish request (v0)"
    )
    request_parser.add_argument("--run-id", required=True, help="Run identifier")

    args = parser.parse_args(argv)
    base_dir = base_dir or REPO_ROOT

    try:
        if args.command == "publish_request":
            generate_publish_request(args.run_id, base_dir=base_dir)
    except Exception as exc:  # pragma: no cover - surfaces CLI errors
        print(f"Error: {exc}")
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(cli_main())
