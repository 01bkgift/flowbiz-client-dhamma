from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from automation_core.contracts.common import _artifact_rel_path, _validate_run_id
from automation_core.contracts.dispatch_audit_v1 import validate_dispatch_audit
from automation_core.contracts.post_content_summary_v1 import (
    validate_post_content_summary,
)
from automation_core.contracts.publish_request_v1 import (
    _compute_idempotency_key,
    validate_publish_request,
)
from automation_core.utils.env import parse_pipeline_enabled

REPO_ROOT = Path(__file__).resolve().parents[2]
ENGINE_NAME = "publish_request_v0"
POST_SUMMARY_NAME = "post_content_summary.json"
DISPATCH_AUDIT_NAME = "dispatch_audit.json"
PUBLISH_REQUEST_NAME = "publish_request.json"
MAX_PREVIEW_CHARS = 500


def _bounded_preview(text: str, limit: int = MAX_PREVIEW_CHARS) -> str:
    if len(text) <= limit:
        return text
    return text[:limit]


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
