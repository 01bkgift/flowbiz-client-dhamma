"""
ตัวช่วยอ่านแผนเวลาและสร้างงานคิวแบบ deterministic
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import yaml
from pydantic import BaseModel, Field, ValidationError, field_validator

from automation_core.queue import FileQueue, JobSpec

DEFAULT_TIMEZONE = "Asia/Bangkok"


class SchedulePlanError(RuntimeError):
    """ข้อผิดพลาดในการอ่านแผนเวลา"""


class ScheduleEntry(BaseModel):
    """รายการแผนเวลา 1 รายการ"""

    publish_at: str = Field(..., min_length=1)
    pipeline_path: str = Field(..., min_length=1)
    run_id_prefix: str | None = None
    params: dict[str, Any] | None = None

    @field_validator("pipeline_path")
    @classmethod
    def _validate_pipeline_path(cls, value: str) -> str:
        """ตรวจสอบ pipeline_path ต้องเป็น relative path และห้ามมี path traversal"""

        path = Path(value)
        if path.is_absolute() or path.drive or path.root:
            raise ValueError("pipeline_path must be relative")
        if any(part == ".." for part in path.parts):
            raise ValueError("pipeline_path must not contain '..'")
        return value


class RawSchedulePlan(BaseModel):
    """ข้อมูลแผนเวลาแบบดิบ"""

    schema_version: str
    timezone: str | None = None
    entries: list[dict[str, Any]] = Field(default_factory=list)


@dataclass(frozen=True)
class ScheduleSkip:
    """เหตุผลที่ข้ามการ enqueue"""

    publish_at: str
    pipeline_path: str
    run_id: str
    code: str
    message: str


@dataclass(frozen=True)
class ScheduleResult:
    """ผลลัพธ์การคัดเลือกงานที่ถึงกำหนด"""

    timezone: str
    enqueued_job_ids: list[str]
    skipped_entries: list[ScheduleSkip]


def parse_iso_datetime(value: str) -> datetime:
    """แปลง ISO8601 ให้รองรับท้าย Z"""

    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


def parse_publish_at(value: str, default_tz: ZoneInfo) -> datetime:
    """แปลง publish_at โดยเติม timezone หากไม่ระบุ"""

    dt = parse_iso_datetime(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=default_tz)
    return dt


def format_utc(value: datetime) -> str:
    """จัดรูปแบบเวลาเป็น UTC แบบมี Z"""

    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def build_run_id_base(local_dt: datetime, run_id_prefix: str | None) -> str:
    """สร้าง run_id พื้นฐาน (ยังไม่รวม job_id)"""

    stamp = local_dt.strftime("%Y%m%d_%H%M")
    if run_id_prefix:
        return f"{run_id_prefix}_{stamp}"
    return stamp


def build_job_id(
    scheduled_for_utc: datetime,
    pipeline_path: str,
    run_id_base: str,
) -> str:
    """สร้าง job_id แบบ deterministic"""

    seed = f"{format_utc(scheduled_for_utc)}|{pipeline_path}|{run_id_base}"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12]


def build_job_spec(
    entry: ScheduleEntry,
    scheduled_for_utc: datetime,
    local_tz: ZoneInfo,
    created_at_utc: datetime,
) -> JobSpec:
    """สร้าง JobSpec จาก ScheduleEntry"""

    local_dt = scheduled_for_utc.astimezone(local_tz)
    run_id_base = build_run_id_base(local_dt, entry.run_id_prefix)
    job_id = build_job_id(scheduled_for_utc, entry.pipeline_path, run_id_base)
    run_id = f"{run_id_base}_{job_id}"
    return JobSpec(
        schema_version="v1",
        job_id=job_id,
        created_at=format_utc(created_at_utc),
        scheduled_for=format_utc(scheduled_for_utc),
        pipeline_path=entry.pipeline_path,
        run_id=run_id,
        params=entry.params,
        status="pending",
        attempts=0,
        last_error=None,
    )


def load_schedule_plan(plan_path: Path) -> RawSchedulePlan:
    """อ่านและตรวจโครงสร้างแผนเวลาเบื้องต้น"""

    try:
        raw = yaml.safe_load(plan_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SchedulePlanError(f"ไม่พบไฟล์แผน: {plan_path}") from exc
    except Exception as exc:  # noqa: BLE001
        raise SchedulePlanError(f"อ่านแผนไม่สำเร็จ: {exc}") from exc

    if not isinstance(raw, dict):
        raise SchedulePlanError("โครงสร้างแผนต้องเป็น dict")

    try:
        plan = RawSchedulePlan.model_validate(raw)
    except ValidationError as exc:
        raise SchedulePlanError(f"โครงสร้างแผนไม่ถูกต้อง: {exc}") from exc

    if plan.schema_version != "v1":
        raise SchedulePlanError("schema_version ต้องเป็น v1")

    return plan


def schedule_due_jobs(
    plan_path: Path,
    queue: FileQueue,
    now_utc: datetime,
    window_minutes: int,
    dry_run: bool,
    scheduler_enabled: bool,
    created_at_utc: datetime | None = None,
) -> ScheduleResult:
    """เลือกงานที่ถึงกำหนดและ enqueue ตามเงื่อนไข"""

    plan = load_schedule_plan(plan_path)
    tz_name = plan.timezone or DEFAULT_TIMEZONE
    try:
        local_tz = ZoneInfo(tz_name)
    except ZoneInfoNotFoundError as exc:
        raise SchedulePlanError(f"timezone ไม่ถูกต้อง: {tz_name}") from exc

    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=UTC)
    else:
        now_utc = now_utc.astimezone(UTC)

    if created_at_utc is None:
        created_at_utc = now_utc

    window_end = now_utc + timedelta(minutes=max(window_minutes, 0))
    enqueued_job_ids: list[str] = []
    skipped_entries: list[ScheduleSkip] = []

    for raw_entry in plan.entries:
        publish_at = ""
        pipeline_path = ""
        try:
            entry = ScheduleEntry.model_validate(raw_entry)
            publish_at = entry.publish_at
            pipeline_path = entry.pipeline_path
            scheduled_local = parse_publish_at(entry.publish_at, local_tz)
            scheduled_utc = scheduled_local.astimezone(UTC)
            job = build_job_spec(entry, scheduled_utc, local_tz, created_at_utc)
        except (ValidationError, ValueError, TypeError) as exc:
            skipped_entries.append(
                ScheduleSkip(
                    publish_at=publish_at,
                    pipeline_path=pipeline_path,
                    run_id="",
                    code="job_invalid",
                    message=str(exc),
                )
            )
            continue

        if not scheduler_enabled:
            skipped_entries.append(
                ScheduleSkip(
                    publish_at=entry.publish_at,
                    pipeline_path=entry.pipeline_path,
                    run_id=job.run_id,
                    code="scheduler_disabled",
                    message="SCHEDULER_ENABLED=false",
                )
            )
            continue

        if not (now_utc <= scheduled_utc <= window_end):
            skipped_entries.append(
                ScheduleSkip(
                    publish_at=entry.publish_at,
                    pipeline_path=entry.pipeline_path,
                    run_id=job.run_id,
                    code="entry_not_due",
                    message="not within window",
                )
            )
            continue

        if dry_run:
            if queue.exists(job.job_id):
                skipped_entries.append(
                    ScheduleSkip(
                        publish_at=entry.publish_at,
                        pipeline_path=entry.pipeline_path,
                        run_id=job.run_id,
                        code="already_enqueued",
                        message="job already exists",
                    )
                )
            else:
                enqueued_job_ids.append(job.job_id)
            continue

        if queue.enqueue(job):
            enqueued_job_ids.append(job.job_id)
        else:
            skipped_entries.append(
                ScheduleSkip(
                    publish_at=entry.publish_at,
                    pipeline_path=entry.pipeline_path,
                    run_id=job.run_id,
                    code="already_enqueued",
                    message="job already exists",
                )
            )

    return ScheduleResult(
        timezone=tz_name,
        enqueued_job_ids=enqueued_job_ids,
        skipped_entries=skipped_entries,
    )
