"""
คิวแบบไฟล์สำหรับจัดการงานที่ต้องรันแบบ deterministic
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError

QueueState = Literal["pending", "running", "done", "failed"]


class JobError(BaseModel):
    """ข้อมูลข้อผิดพลาดของงานในคิว"""

    code: str
    message: str


class JobSpec(BaseModel):
    """สคีมางานคิวเวอร์ชัน v1"""

    schema_version: Literal["v1"] = Field(default="v1")
    job_id: str
    created_at: str
    scheduled_for: str
    pipeline_path: str
    run_id: str
    params: dict[str, Any] | None = None
    status: QueueState
    attempts: int = 0
    last_error: JobError | None = None


@dataclass(frozen=True)
class QueueItem:
    """รายการงานในคิวพร้อมพาธไฟล์"""

    filename: str
    path: Path
    job: JobSpec | None
    job_id: str


def _parse_iso_datetime(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt


def _format_compact_utc(value: str) -> str:
    dt = _parse_iso_datetime(value).astimezone(UTC)
    return dt.strftime("%Y%m%dT%H%M%SZ")


def _job_id_from_filename(filename: str) -> str:
    stem = Path(filename).stem
    parts = stem.split("_", 1)
    if len(parts) == 2:
        return parts[1]
    return stem


class FileQueue:
    """คิวไฟล์แบบ deterministic"""

    def __init__(self, queue_dir: Path | str) -> None:
        self.queue_dir = Path(queue_dir)
        self.pending_dir = self.queue_dir / "pending"
        self.running_dir = self.queue_dir / "running"
        self.done_dir = self.queue_dir / "done"
        self.failed_dir = self.queue_dir / "failed"

    def _ensure_dirs(self) -> None:
        for path in [
            self.pending_dir,
            self.running_dir,
            self.done_dir,
            self.failed_dir,
        ]:
            path.mkdir(parents=True, exist_ok=True)

    def _write_job(self, path: Path, job: JobSpec) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_suffix(f"{path.suffix}.tmp.{os.getpid()}")
        payload = json.dumps(job.model_dump(), ensure_ascii=False, indent=2)
        temp_path.write_text(payload, encoding="utf-8")
        os.replace(temp_path, path)

    def _load_job(self, path: Path) -> JobSpec | None:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        try:
            return JobSpec.model_validate(data)
        except ValidationError:
            return None

    def _build_filename(self, job: JobSpec) -> str:
        scheduled_compact = _format_compact_utc(job.scheduled_for)
        return f"{scheduled_compact}_{job.job_id}.json"

    def _list_dir(self, path: Path) -> list[Path]:
        if not path.exists():
            return []
        return sorted(path.glob("*.json"))

    def _find_by_job_id(self, job_id: str) -> list[Path]:
        pattern = f"*_{job_id}.json"
        matches: list[Path] = []
        for path in [
            self.pending_dir,
            self.running_dir,
            self.done_dir,
            self.failed_dir,
        ]:
            if path.exists():
                matches.extend(path.glob(pattern))
        return matches

    def exists(self, job_id: str) -> bool:
        """ตรวจว่ามีงานอยู่ในคิวทุกสถานะหรือไม่"""

        return bool(self._find_by_job_id(job_id))

    def enqueue(self, job: JobSpec) -> bool:
        """เพิ่มงานลงคิวแบบ idempotent"""

        self._ensure_dirs()
        if self.exists(job.job_id):
            return False
        pending_job = job.model_copy(update={"status": "pending", "last_error": None})
        target_path = self.pending_dir / self._build_filename(pending_job)
        payload = json.dumps(pending_job.model_dump(), ensure_ascii=False, indent=2)

        try:
            # ใช้โหมด "x" เพื่อสร้างไฟล์แบบ exclusive และเขียนข้อมูลในขั้นตอนเดียว
            with open(target_path, "x", encoding="utf-8") as f:
                f.write(payload)
        except FileExistsError:
            # มีงานที่ job_id เดียวกันถูก enqueue ไปแล้ว
            return False
        else:
            return True

    def list_pending(self) -> list[QueueItem]:
        """คืนรายการงานในสถานะ pending ตามลำดับ FIFO"""

        items: list[QueueItem] = []
        for path in self._list_dir(self.pending_dir):
            job = self._load_job(path)
            items.append(
                QueueItem(
                    filename=path.name,
                    path=path,
                    job=job,
                    job_id=_job_id_from_filename(path.name),
                )
            )
        return items

    def peek_next(self) -> QueueItem | None:
        """ดูงานถัดไปแบบไม่ย้ายสถานะ"""

        pending = self.list_pending()
        if not pending:
            return None
        return pending[0]

    def dequeue_next(self) -> QueueItem | None:
        """ย้ายงานถัดไปจาก pending ไป running"""

        pending = self.list_pending()
        if not pending:
            return None
        item = pending[0]
        self._ensure_dirs()
        dest_path = self.running_dir / item.filename
        try:
            os.replace(item.path, dest_path)
        except FileNotFoundError:
            # งานถูก dequeue โดย worker ตัวอื่นไปแล้ว
            return None
        job = item.job
        if job is not None:
            job = job.model_copy(
                update={
                    "status": "running",
                    "attempts": job.attempts + 1,
                    "last_error": None,
                }
            )
            self._write_job(dest_path, job)
        return QueueItem(
            filename=item.filename,
            path=dest_path,
            job=job,
            job_id=item.job_id,
        )

    def mark_done(self, item: QueueItem) -> QueueItem:
        """ย้ายงานจาก running ไป done"""

        self._ensure_dirs()
        src_path = self.running_dir / item.filename
        dest_path = self.done_dir / item.filename
        os.replace(src_path, dest_path)
        job = item.job
        if job is not None:
            job = job.model_copy(update={"status": "done", "last_error": None})
            self._write_job(dest_path, job)
        return QueueItem(
            filename=item.filename,
            path=dest_path,
            job=job,
            job_id=item.job_id,
        )

    def mark_failed(self, item: QueueItem, error: JobError | None = None) -> QueueItem:
        """ย้ายงานจาก running ไป failed"""

        self._ensure_dirs()
        src_path = self.running_dir / item.filename
        dest_path = self.failed_dir / item.filename
        os.replace(src_path, dest_path)
        job = item.job
        if job is not None:
            update: dict[str, Any] = {"status": "failed"}
            if error is not None:
                update["last_error"] = error
            job = job.model_copy(update=update)
            self._write_job(dest_path, job)
        return QueueItem(
            filename=item.filename,
            path=dest_path,
            job=job,
            job_id=item.job_id,
        )
