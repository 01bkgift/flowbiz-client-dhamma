from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from automation_core.contracts import dispatch_audit_v1 as _dispatch_audit_contracts
from automation_core.contracts import post_content_summary_v1 as _post_summary_contracts
from automation_core.contracts.common import _validate_run_id
from automation_core.dispatch.adapters import DispatchAdapterError, get_adapter
from automation_core.utils.env import parse_pipeline_enabled

validate_dispatch_audit = _dispatch_audit_contracts.validate_dispatch_audit
_build_actions = _dispatch_audit_contracts._build_actions
validate_post_content_summary = _post_summary_contracts.validate_post_content_summary
_post_summary_rel_path = _post_summary_contracts._post_summary_rel_path

REPO_ROOT = Path(__file__).resolve().parents[2]
ENGINE_NAME = "dispatch_v0"
POST_SUMMARY_NAME = "post_content_summary.json"
AUDIT_NAME = "dispatch_audit.json"
MAX_PREVIEW_CHARS = 500
TRUE_VALUES = {"true", "1", "yes", "on", "enabled"}
ALLOWED_MODES = {"dry_run", "print_only"}


class DispatchModeError(ValueError):
    def __init__(self, *, code: str, requested_mode: str, message: str):
        super().__init__(message)
        self.code = code
        self.requested_mode = requested_mode


def parse_dispatch_enabled(value: str | None) -> bool:
    """
    แปลงค่าจากตัวแปรสภาพแวดล้อม DISPATCH_ENABLED ให้เป็น boolean
    ค่าเริ่มต้นเป็น False (ปิด) เมื่อไม่กำหนด เพื่อความปลอดภัยแบบ dry-run

    Args:
        value: ค่าจากตัวแปรสภาพแวดล้อมหรือ None

    Returns:
        bool: True ถ้าเป็นค่าที่ตีความว่าเปิดใช้งาน, False ในกรณีอื่น
    """
    if value is None:
        return False
    return value.strip().lower() in TRUE_VALUES


def _validate_dispatch_mode(raw_mode: str | None) -> str:
    """ตรวจสอบโหมด dispatch ให้เป็นค่าที่รองรับ"""
    if raw_mode is None or not raw_mode.strip():
        return "dry_run"
    mode = raw_mode.strip().lower()
    if mode in ALLOWED_MODES:
        return mode
    if mode == "publish":
        raise DispatchModeError(
            code="publish_not_supported",
            requested_mode=mode,
            message="DISPATCH_MODE=publish is not supported (audit-only)",
        )
    raise DispatchModeError(
        code="invalid_argument",
        requested_mode=mode,
        message="DISPATCH_MODE must be one of: dry_run, print_only",
    )


def _bounded_preview(text: str, limit: int = MAX_PREVIEW_CHARS) -> str:
    """ตัดข้อความให้ไม่เกิน limit ตัวอักษร"""
    if len(text) <= limit:
        return text
    return text[:limit]


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
    relative = _post_summary_rel_path(run_id, validate=False)
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
) -> tuple[dict[str, Any], Path | None]:
    """
    สร้างและเขียน dispatch_audit.json จาก post_content_summary.json
    """
    run_id = _validate_run_id(run_id)
    if not parse_pipeline_enabled(os.environ.get("PIPELINE_ENABLED")):
        print("Pipeline disabled by PIPELINE_ENABLED=false")
        return {}, None

    # pre-compute defaults for failure audit paths
    post_summary_rel = _post_summary_rel_path(run_id, validate=False)
    enabled = (
        dispatch_enabled
        if dispatch_enabled is not None
        else parse_dispatch_enabled(os.environ.get("DISPATCH_ENABLED"))
    )
    target = dispatch_target or os.environ.get("DISPATCH_TARGET") or ""
    platform = ""
    short_bytes = 0
    long_bytes = 0
    adapter = None
    # defaults above are reused for failure audit paths
    try:
        post_summary_rel, post_summary = load_post_content_summary(run_id, base_dir)
        platform = str(post_summary["inputs"]["platform"])
        target = target or platform
        short_text = post_summary["outputs"]["short"]
        long_text = post_summary["outputs"]["long"]
        short_bytes = len(short_text.encode("utf-8"))
        long_bytes = len(long_text.encode("utf-8"))
        mode = _validate_dispatch_mode(dispatch_mode or os.environ.get("DISPATCH_MODE"))

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

        adapter = get_adapter(target, platform)
        actions = adapter.build_actions(
            short_bytes=short_bytes,
            long_bytes=long_bytes,
            publish_reason=publish_reason,
            target=target,
        )
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
            audit_path.relative_to(base_dir).as_posix()
            if audit_path is not None
            else ""
        )
        print(f"Dispatch v0: status={status} audit={audit_rel or 'skipped'}")
        return audit, audit_path
    except (
        FileNotFoundError,
        json.JSONDecodeError,
        ValueError,
        DispatchAdapterError,
    ) as exc:
        if isinstance(exc, FileNotFoundError):
            error_code = "file_not_found"
        elif isinstance(exc, json.JSONDecodeError):
            error_code = "invalid_json"
        elif isinstance(exc, DispatchModeError):
            error_code = exc.code
        elif isinstance(exc, DispatchAdapterError):
            error_code = exc.code
        elif isinstance(exc, ValueError) and str(exc).startswith("Invalid JSON in "):
            error_code = "invalid_json"
        else:
            # ใช้สำหรับโหมดหรือค่าพารามิเตอร์ที่ไม่ถูกต้อง
            error_code = "invalid_argument"

        if isinstance(exc, DispatchModeError):
            detail: Any = {"requested_mode": exc.requested_mode}
        elif isinstance(exc, DispatchAdapterError):
            detail = {"target": target or "unknown", "platform": platform or "unknown"}
        else:
            detail = {"type": type(exc).__name__, "message": str(exc)}

        errors = [
            {
                "code": error_code,
                "message": "Dispatch failed - see detail",
                "step": "dispatch.v0",
                "detail": detail,
            }
        ]
        adapter_name = adapter.name if adapter is not None else "unknown"
        failure_target = target or "unknown"
        failure_actions = (
            adapter.build_actions(
                short_bytes=short_bytes,
                long_bytes=long_bytes,
                publish_reason="failure",
                target=failure_target,
            )
            if adapter is not None
            else _build_actions(
                short_bytes,
                long_bytes,
                "failure",
                target=failure_target,
                adapter=adapter_name,
            )
        )
        failure_audit = build_dispatch_audit(
            run_id=run_id,
            post_content_summary=post_summary_rel,
            dispatch_enabled=enabled,
            dispatch_mode="dry_run",
            target=failure_target,
            platform=platform or "unknown",
            status="failed",
            message="Dispatch failed - see errors",
            actions=failure_actions,
            errors=errors,
            checked_at=checked_at,
        )
        audit_path = write_dispatch_audit(run_id, failure_audit, base_dir=base_dir)
        audit_rel = (
            audit_path.relative_to(base_dir).as_posix()
            if audit_path is not None
            else ""
        )
        print(f"Dispatch v0: status=failed audit={audit_rel or 'skipped'}")
        print("Dispatch v0: wrote failure audit then raising (fail-fast)")
        raise


def cli_main(argv: list[str] | None = None, base_dir: Path | None = None) -> int:
    """
    CLI สำหรับรัน dispatch_v0 (audit mode)

    หมายเหตุ:
        - CLI นี้เรียกใช้ generate_dispatch_audit ซึ่งตรวจสอบค่า PIPELINE_ENABLED
          ตาม kill switch ของระบบ จึงไม่รัน pipeline เมื่อถูกปิดใช้งาน
        - สำหรับการใช้งานจริงใน production แนะนำให้เรียกผ่าน orchestrator.py
          หรือ web runner เพื่อให้ได้การตรวจสอบ operational guards ครบถ้วน
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
