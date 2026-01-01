"""
สคริปต์ scheduler/worker แบบ cron-friendly สำหรับงานคิว
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automation_core.queue import FileQueue, JobError, QueueItem  # noqa: E402
from automation_core.scheduler import (  # noqa: E402
    DEFAULT_TIMEZONE,
    SchedulePlanError,
    parse_iso_datetime,
    schedule_due_jobs,
)
from orchestrator import parse_pipeline_enabled  # noqa: E402


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _utc_iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    _ensure_dir(path.parent)
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    path.write_text(text, encoding="utf-8")


def _parse_enabled_flag(env_value: str | None) -> bool:
    if env_value is None:
        return False
    return env_value.strip().lower() in ("true", "1", "yes", "on", "enabled")


def _resolve_path(base_dir: Path, value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return base_dir / path


def _relative_path(base_dir: Path, path: Path) -> str:
    try:
        return path.relative_to(base_dir).as_posix()
    except ValueError:
        return path.as_posix()


def _schedule_summary_path(base_dir: Path, now_utc: datetime, tz_name: str) -> Path:
    try:
        local_dt = now_utc.astimezone(ZoneInfo(tz_name))
    except ZoneInfoNotFoundError:
        # ถ้า timezone ไม่ถูกต้อง ใช้ timezone เริ่มต้น
        local_dt = now_utc.astimezone(ZoneInfo(DEFAULT_TIMEZONE))
    date_stamp = local_dt.strftime("%Y%m%d")
    return (
        base_dir
        / "output"
        / "scheduler"
        / "artifacts"
        / (f"schedule_summary_{date_stamp}.json")
    )


def _worker_summary_path(base_dir: Path, job_id: str) -> Path:
    safe_job_id = job_id or "none"
    return (
        base_dir
        / "output"
        / "worker"
        / "artifacts"
        / (f"worker_summary_{safe_job_id}.json")
    )


def _build_schedule_summary(
    plan_path: Path,
    now_utc: datetime,
    window_minutes: int,
    enqueued_job_ids: list[str],
    skipped_entries: list[dict[str, Any]],
    dry_run: bool,
    base_dir: Path,
) -> dict[str, Any]:
    return {
        "schema_version": "v1",
        "engine": "scheduler",
        "checked_at": _utc_iso(_utc_now()),
        "plan_path": _relative_path(base_dir, plan_path),
        "now": _utc_iso(now_utc),
        "window_minutes": window_minutes,
        "enqueued_job_ids": enqueued_job_ids,
        "skipped_entries": skipped_entries,
        "dry_run": dry_run,
    }


def run_schedule(
    plan_path: str | Path,
    queue_dir: str | Path,
    now: datetime | None,
    window_minutes: int,
    dry_run: bool,
    base_dir: Path = ROOT,
) -> dict[str, Any] | None:
    pipeline_enabled = parse_pipeline_enabled(os.environ.get("PIPELINE_ENABLED"))
    if not pipeline_enabled:
        print("Pipeline disabled by PIPELINE_ENABLED=false")
        return None

    scheduler_enabled = dry_run or _parse_enabled_flag(
        os.environ.get("SCHEDULER_ENABLED")
    )
    now_utc = now or _utc_now()
    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=UTC)
    else:
        now_utc = now_utc.astimezone(UTC)

    plan_path = _resolve_path(base_dir, plan_path)
    queue_dir = _resolve_path(base_dir, queue_dir)
    queue = FileQueue(queue_dir)

    try:
        result = schedule_due_jobs(
            plan_path=plan_path,
            queue=queue,
            now_utc=now_utc,
            window_minutes=window_minutes,
            dry_run=dry_run,
            scheduler_enabled=scheduler_enabled,
            created_at_utc=_utc_now(),
        )
        skipped_entries = [
            {
                "publish_at": item.publish_at,
                "pipeline_path": item.pipeline_path,
                "run_id": item.run_id,
                "code": item.code,
                "message": item.message,
            }
            for item in result.skipped_entries
        ]
        summary = _build_schedule_summary(
            plan_path=plan_path,
            now_utc=now_utc,
            window_minutes=window_minutes,
            enqueued_job_ids=result.enqueued_job_ids,
            skipped_entries=skipped_entries,
            dry_run=dry_run,
            base_dir=base_dir,
        )
        summary_path = _schedule_summary_path(base_dir, now_utc, result.timezone)
        _write_json(summary_path, summary)
        return summary
    except SchedulePlanError as exc:
        summary = _build_schedule_summary(
            plan_path=plan_path,
            now_utc=now_utc,
            window_minutes=window_minutes,
            enqueued_job_ids=[],
            skipped_entries=[
                {
                    "publish_at": "",
                    "pipeline_path": "",
                    "run_id": "",
                    "code": "plan_parse_error",
                    "message": str(exc),
                }
            ],
            dry_run=dry_run,
            base_dir=base_dir,
        )
        summary_path = _schedule_summary_path(base_dir, now_utc, DEFAULT_TIMEZONE)
        _write_json(summary_path, summary)
        return summary


def _build_worker_summary(
    job_id: str,
    run_id: str,
    pipeline_path: str,
    decision: str,
    error: JobError | None,
    dry_run: bool,
) -> dict[str, Any]:
    payload = {
        "schema_version": "v1",
        "engine": "worker",
        "checked_at": _utc_iso(_utc_now()),
        "job_id": job_id,
        "run_id": run_id,
        "pipeline_path": pipeline_path,
        "decision": decision,
        "error": None,
        "dry_run": dry_run,
    }
    if error is not None:
        payload["error"] = {"code": error.code, "message": error.message}
    return payload


def _extract_job_fields(item: QueueItem | None) -> tuple[str, str, str]:
    if item is None:
        return "none", "", ""
    job_id = item.job_id or "none"
    if item.job is None:
        return job_id, "", ""
    return job_id, item.job.run_id, item.job.pipeline_path


def run_worker(
    queue_dir: str | Path,
    dry_run: bool,
    base_dir: Path = ROOT,
    pipeline_runner: Callable[[Path, str], Any] | None = None,
) -> dict[str, Any] | None:
    pipeline_enabled = parse_pipeline_enabled(os.environ.get("PIPELINE_ENABLED"))
    if not pipeline_enabled:
        print("Pipeline disabled by PIPELINE_ENABLED=false")
        return None

    worker_enabled = dry_run or _parse_enabled_flag(os.environ.get("WORKER_ENABLED"))
    queue_dir = _resolve_path(base_dir, queue_dir)
    queue = FileQueue(queue_dir)

    if not worker_enabled:
        peek = queue.peek_next()
        job_id, run_id, pipeline_path = _extract_job_fields(peek)
        summary = _build_worker_summary(
            job_id=job_id,
            run_id=run_id,
            pipeline_path=pipeline_path,
            decision="skipped",
            error=JobError(code="worker_disabled", message="WORKER_ENABLED=false"),
            dry_run=dry_run,
        )
        summary_path = _worker_summary_path(base_dir, job_id)
        _write_json(summary_path, summary)
        return summary

    if dry_run:
        peek = queue.peek_next()
        job_id, run_id, pipeline_path = _extract_job_fields(peek)
        if peek is None:
            error = JobError(code="queue_empty", message="no pending job")
        elif peek.job is None:
            error = JobError(code="job_invalid", message="invalid job payload")
        else:
            error = None
        summary = _build_worker_summary(
            job_id=job_id,
            run_id=run_id,
            pipeline_path=pipeline_path,
            decision="skipped",
            error=error,
            dry_run=dry_run,
        )
        summary_path = _worker_summary_path(base_dir, job_id)
        _write_json(summary_path, summary)
        return summary

    item = queue.dequeue_next()
    if item is None:
        summary = _build_worker_summary(
            job_id="none",
            run_id="",
            pipeline_path="",
            decision="skipped",
            error=JobError(code="queue_empty", message="no pending job"),
            dry_run=dry_run,
        )
        summary_path = _worker_summary_path(base_dir, "none")
        _write_json(summary_path, summary)
        return summary

    job_id, run_id, pipeline_path = _extract_job_fields(item)
    if item.job is None:
        queue.mark_failed(
            item,
            JobError(code="job_invalid", message="invalid job payload"),
        )
        summary = _build_worker_summary(
            job_id=job_id,
            run_id=run_id,
            pipeline_path=pipeline_path,
            decision="failed",
            error=JobError(code="job_invalid", message="invalid job payload"),
            dry_run=dry_run,
        )
        summary_path = _worker_summary_path(base_dir, job_id)
        _write_json(summary_path, summary)
        return summary

    if pipeline_runner is None:
        from orchestrator import run_pipeline  # noqa: E402

        pipeline_runner = run_pipeline

    try:
        pipeline_path_obj = Path(item.job.pipeline_path)
        if not pipeline_path_obj.is_absolute():
            pipeline_path_obj = base_dir / pipeline_path_obj
        # ป้องกัน path traversal โดย resolve path และตรวจสอบว่าต้องอยู่ภายใน base_dir เท่านั้น
        base_dir_resolved = base_dir.resolve()
        pipeline_path_obj = pipeline_path_obj.resolve()
        try:
            pipeline_path_obj.relative_to(base_dir_resolved)
        except ValueError as exc:
            raise ValueError(
                f"invalid pipeline path outside base dir: {pipeline_path_obj}"
            ) from exc
        pipeline_runner(pipeline_path_obj, item.job.run_id)
        queue.mark_done(item)
        summary = _build_worker_summary(
            job_id=job_id,
            run_id=run_id,
            pipeline_path=pipeline_path,
            decision="done",
            error=None,
            dry_run=dry_run,
        )
        summary_path = _worker_summary_path(base_dir, job_id)
        _write_json(summary_path, summary)
        return summary
    except Exception as exc:  # noqa: BLE001
        queue.mark_failed(item, JobError(code="orchestrator_failed", message=str(exc)))
        summary = _build_worker_summary(
            job_id=job_id,
            run_id=run_id,
            pipeline_path=pipeline_path,
            decision="failed",
            error=JobError(code="orchestrator_failed", message=str(exc)),
            dry_run=dry_run,
        )
        summary_path = _worker_summary_path(base_dir, job_id)
        _write_json(summary_path, summary)
        return summary


def run_queue_list(queue_dir: str | Path, base_dir: Path = ROOT) -> None:
    queue_dir = _resolve_path(base_dir, queue_dir)
    queue = FileQueue(queue_dir)
    for item in queue.list_pending():
        print(item.filename)


def _parse_now(now_value: str | None) -> datetime | None:
    if now_value is None:
        return None
    dt = parse_iso_datetime(now_value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Cron-friendly scheduler/worker runner"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    schedule_parser = subparsers.add_parser("schedule", help="enqueue due jobs")
    schedule_parser.add_argument(
        "--plan",
        default="scripts/schedule_plan.yaml",
        help="path to schedule plan",
    )
    schedule_parser.add_argument(
        "--now",
        default=None,
        help="override current time (ISO8601)",
    )
    schedule_parser.add_argument(
        "--window-minutes",
        type=int,
        default=10,
        help="window in minutes",
    )
    schedule_parser.add_argument(
        "--queue-dir",
        default="data/queue",
        help="queue directory",
    )
    schedule_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="run without enqueue",
    )

    work_parser = subparsers.add_parser("work", help="work one job")
    work_parser.add_argument(
        "--queue-dir",
        default="data/queue",
        help="queue directory",
    )
    work_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="run without orchestrator execution",
    )

    queue_parser = subparsers.add_parser("queue", help="queue operations")
    queue_subparsers = queue_parser.add_subparsers(dest="queue_command", required=True)
    list_parser = queue_subparsers.add_parser("list", help="list pending jobs")
    list_parser.add_argument(
        "--queue-dir",
        default="data/queue",
        help="queue directory",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "schedule":
        now_dt = _parse_now(args.now)
        run_schedule(
            plan_path=args.plan,
            queue_dir=args.queue_dir,
            now=now_dt,
            window_minutes=args.window_minutes,
            dry_run=args.dry_run,
        )
        return 0

    if args.command == "work":
        summary = run_worker(
            queue_dir=args.queue_dir,
            dry_run=args.dry_run,
        )
        if summary and summary.get("decision") == "failed":
            return 1
        return 0

    if args.command == "queue" and args.queue_command == "list":
        run_queue_list(queue_dir=args.queue_dir)
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
