from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from automation_core.utils.env import parse_pipeline_enabled

REPO_ROOT = Path(__file__).resolve().parents[2]
ENGINE_NAME = "dispatch_v0"
POST_SUMMARY_NAME = "post_content_summary.json"
AUDIT_NAME = "dispatch_audit.json"
MAX_PREVIEW_CHARS = 500
TRUE_VALUES = {"true", "1", "yes", "on", "enabled"}
ALLOWED_MODES = {"dry_run", "print_only"}


def parse_dispatch_enabled(value: str | None) -> bool:
    """
    แปลงค่าจากตัวแปรสภาพแวดล้อม DISPATCH_ENABLED ให้เป็น boolean

    Args:
        value: ค่าจากตัวแปรสภาพแวดล้อมหรือ None

    Returns:
        bool: True ถ้าเป็นค่าที่ตีความว่าเปิดใช้งาน, False ในกรณีอื่น
    """
    if value is None:
        return False
    return value.strip().lower() in TRUE_VALUES


def _validate_run_id(run_id: str) -> str:
    """ตรวจสอบว่า run_id เป็น path segment เดียวและไม่ใช่ absolute path"""
    path = Path(run_id)
    if not run_id or path.is_absolute() or path.drive or path.root:
        raise ValueError("run_id must be a relative path segment")
    if len(path.parts) != 1 or any(part in (".", "..") for part in path.parts):
        raise ValueError("run_id must not contain path separators or traversal")
    return run_id


def _validate_dispatch_mode(raw_mode: str | None) -> str:
    """ตรวจสอบโหมด dispatch ให้เป็นค่าที่รองรับ"""
    if raw_mode is None or not raw_mode.strip():
        return "dry_run"
    mode = raw_mode.strip().lower()
    if mode not in ALLOWED_MODES:
        raise ValueError("DISPATCH_MODE must be one of: dry_run, print_only")
    return mode


def _bounded_preview(text: str, limit: int = MAX_PREVIEW_CHARS) -> str:
    """ตัดข้อความให้ไม่เกิน limit ตัวอักษร"""
    if len(text) <= limit:
        return text
    return text[:limit]


def validate_post_content_summary(data: dict[str, Any], run_id: str) -> dict[str, Any]:
    """
    ตรวจสอบ post_content_summary เบื้องต้นตามสัญญา v1

    Args:
        data: เนื้อหา JSON ของ post_content_summary
        run_id: run id ที่คาดหวังให้ตรงกัน

    Returns:
        dict[str, Any]: ข้อมูลเดิมที่ผ่านการตรวจสอบ

    Raises:
        ValueError: เมื่อข้อมูลไม่ตรงตามข้อกำหนดขั้นต่ำ
    """
    if not isinstance(data, dict):
        raise ValueError("post_content_summary must be an object")
    if data.get("schema_version") != "v1":
        raise ValueError("post_content_summary.schema_version must be 'v1'")
    if data.get("engine") != "post_templates":
        raise ValueError("post_content_summary.engine must be 'post_templates'")
    summary_run_id = data.get("run_id")
    if summary_run_id is None or summary_run_id != run_id:
        raise ValueError("post_content_summary.run_id must match run_id")

    inputs = data.get("inputs")
    if not isinstance(inputs, dict):
        raise ValueError("post_content_summary.inputs must be an object")
    platform = inputs.get("platform")
    if not isinstance(platform, str) or not platform.strip():
        raise ValueError("post_content_summary.inputs.platform is required")

    outputs = data.get("outputs")
    if not isinstance(outputs, dict):
        raise ValueError("post_content_summary.outputs must be an object")
    for key in ("short", "long"):
        value = outputs.get(key)
        if not isinstance(value, str):
            raise ValueError(f"post_content_summary.outputs.{key} must be a string")
    return data


def load_post_content_summary(
    run_id: str, base_dir: Path = REPO_ROOT
) -> tuple[str, dict[str, Any]]:
    """
    โหลด post_content_summary.json สำหรับ run_id ที่กำหนด

    Args:
        run_id: รหัสการรัน
        base_dir: โฟลเดอร์ฐานของ repo

    Returns:
        tuple[str, dict[str, Any]]: (relative path, json data ที่ validate แล้ว)
    """
    run_id = _validate_run_id(run_id)
    relative = (Path("output") / run_id / "artifacts" / POST_SUMMARY_NAME).as_posix()
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


def build_dispatch_audit(
    *,
    run_id: str,
    post_content_summary: str,
    dispatch_enabled: bool,
    dispatch_mode: str,
    target: str,
    platform: str,
    status: str,
    message: str,
    actions: list[dict[str, Any]],
    errors: list[dict[str, Any]] | None = None,
    checked_at: datetime | None = None,
) -> dict[str, Any]:
    """สร้าง payload สำหรับ dispatch_audit.json"""
    checked = (checked_at or datetime.now(tz=UTC)).isoformat().replace("+00:00", "Z")
    return {
        "schema_version": "v1",
        "engine": ENGINE_NAME,
        "run_id": run_id,
        "checked_at": checked,
        "inputs": {
            "post_content_summary": post_content_summary,
            "dispatch_enabled": dispatch_enabled,
            "dispatch_mode": dispatch_mode,
            "target": target,
            "platform": platform,
        },
        "result": {
            "status": status,
            "message": message,
            "actions": actions,
        },
        "errors": errors or [],
    }


def write_dispatch_audit(
    run_id: str, audit: dict[str, Any], base_dir: Path = REPO_ROOT
) -> Path | None:
    """
    เขียนไฟล์ dispatch_audit.json (เคารพ PIPELINE_ENABLED)
    """
    run_id = _validate_run_id(run_id)
    output_path = base_dir / "output" / run_id / "artifacts" / AUDIT_NAME
    if not parse_pipeline_enabled(os.environ.get("PIPELINE_ENABLED")):
        return None
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), "utf-8")
    return output_path


def generate_dispatch_audit(
    run_id: str,
    *,
    base_dir: Path = REPO_ROOT,
    dispatch_enabled: bool | None = None,
    dispatch_mode: str | None = None,
    dispatch_target: str | None = None,
    checked_at: datetime | None = None,
) -> tuple[dict[str, Any] | None, Path | None]:
    """
    สร้างและเขียน dispatch_audit.json จาก post_content_summary.json
    """
    run_id = _validate_run_id(run_id)
    if not parse_pipeline_enabled(os.environ.get("PIPELINE_ENABLED")):
        print("Pipeline disabled by PIPELINE_ENABLED=false")
        return None, None

    post_summary_rel, post_summary = load_post_content_summary(run_id, base_dir)
    mode = _validate_dispatch_mode(dispatch_mode or os.environ.get("DISPATCH_MODE"))
    enabled = (
        dispatch_enabled
        if dispatch_enabled is not None
        else parse_dispatch_enabled(os.environ.get("DISPATCH_ENABLED"))
    )

    platform = str(post_summary["inputs"]["platform"])
    target = dispatch_target or os.environ.get("DISPATCH_TARGET") or platform
    short_text = post_summary["outputs"]["short"]
    long_text = post_summary["outputs"]["long"]
    short_bytes = len(short_text.encode("utf-8"))
    long_bytes = len(long_text.encode("utf-8"))

    print(f"Dispatch v0: start run_id={run_id}")
    print(f"Dispatch v0: target={target} mode={mode} enabled={enabled}")
    print(f"Dispatch v0: short bytes={short_bytes}")
    print(_bounded_preview(short_text))
    print(f"Dispatch v0: long bytes={long_bytes}")
    print(_bounded_preview(long_text))

    if not enabled:
        status = "skipped"
        message = "Dispatch disabled (DISPATCH_ENABLED=false or unset)"
        publish_reason = "dispatch disabled"
    elif mode == "print_only":
        status = "printed"
        message = "Printed content only (print_only mode)"
        publish_reason = "print_only mode"
    else:
        status = "dry_run"
        message = "Dispatch dry-run (no external publish)"
        publish_reason = "dry_run default"

    actions: list[dict[str, Any]] = [
        {"type": "print", "label": "short", "bytes": short_bytes},
        {"type": "print", "label": "long", "bytes": long_bytes},
        {"type": "noop", "label": "publish", "reason": publish_reason},
    ]

    audit = build_dispatch_audit(
        run_id=run_id,
        post_content_summary=post_summary_rel,
        dispatch_enabled=enabled,
        dispatch_mode=mode,
        target=target,
        platform=platform,
        status=status,
        message=message,
        actions=actions,
        errors=[],
        checked_at=checked_at,
    )

    audit_path = write_dispatch_audit(run_id, audit, base_dir=base_dir)
    audit_rel = (
        audit_path.relative_to(base_dir).as_posix() if audit_path is not None else ""
    )
    print(f"Dispatch v0: status={status} audit={audit_rel or 'skipped'}")
    return audit, audit_path


def cli_main(argv: list[str] | None = None, base_dir: Path | None = None) -> int:
    """
    CLI สำหรับรัน dispatch_v0
    """
    parser = argparse.ArgumentParser(
        description="Dispatch v0 - audit-only (dry-run default)"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    dispatch_parser = subparsers.add_parser("dispatch", help="Run dispatch audit (v0)")
    dispatch_parser.add_argument("--run-id", required=True, help="Run identifier")

    args = parser.parse_args(argv)
    base_dir = base_dir or REPO_ROOT

    try:
        if args.command == "dispatch":
            generate_dispatch_audit(args.run_id, base_dir=base_dir)
    except Exception as exc:  # pragma: no cover - surfaces CLI errors
        print(f"Error: {exc}")
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(cli_main())
