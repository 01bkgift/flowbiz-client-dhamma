"""ทดสอบการทำงานของคิวไฟล์

หมายเหตุ: การทดสอบ concurrency
- คิวใช้ os.O_CREAT | os.O_EXCL สำหรับ enqueue (ป้องกัน race condition)
- dequeue_next มีการจัดการ FileNotFoundError (สำหรับ race condition)
- ออกแบบสำหรับ single-worker execution
- การรัน worker หลายตัวพร้อมกันไม่แนะนำ แต่จะไม่ทำให้เกิด data corruption
- ถ้าต้องการ parallel processing ให้ใช้ external locking (เช่น flock)
"""

from datetime import UTC, datetime, timedelta
from pathlib import Path

from automation_core.queue import FileQueue, JobError, JobSpec


def _utc_iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _build_job(job_id: str, scheduled_for: datetime, run_id: str) -> JobSpec:
    return JobSpec(
        schema_version="v1",
        job_id=job_id,
        created_at=_utc_iso(datetime.now(UTC)),
        scheduled_for=_utc_iso(scheduled_for),
        pipeline_path="pipeline.web.yml",
        run_id=run_id,
        params=None,
        status="pending",
        attempts=0,
        last_error=None,
    )


def test_enqueue_idempotent(tmp_path: Path):
    queue = FileQueue(tmp_path / "queue")
    now = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    job = _build_job("job-001", now, "run_001")

    assert queue.enqueue(job) is True
    assert queue.enqueue(job) is False

    pending = queue.list_pending()
    assert len(pending) == 1
    assert pending[0].job_id == "job-001"


def test_fifo_ordering_by_schedule(tmp_path: Path):
    queue = FileQueue(tmp_path / "queue")
    now = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    job_early = _build_job("job-early", now, "run_early")
    job_late = _build_job("job-late", now + timedelta(minutes=5), "run_late")

    queue.enqueue(job_late)
    queue.enqueue(job_early)

    pending = queue.list_pending()
    assert [item.job_id for item in pending] == ["job-early", "job-late"]


def test_state_transitions(tmp_path: Path):
    queue = FileQueue(tmp_path / "queue")
    now = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    job_done = _build_job("job-done", now, "run_done")
    job_failed = _build_job("job-failed", now + timedelta(minutes=1), "run_fail")

    queue.enqueue(job_done)
    queue.enqueue(job_failed)

    first = queue.dequeue_next()
    assert first is not None
    assert first.job is not None
    assert first.job.status == "running"
    assert first.job.attempts == 1

    done_item = queue.mark_done(first)
    assert done_item.job is not None
    assert done_item.job.status == "done"
    assert (queue.done_dir / done_item.filename).exists()

    second = queue.dequeue_next()
    assert second is not None
    assert second.job is not None
    error = JobError(code="test_error", message="fail")
    failed_item = queue.mark_failed(second, error)

    assert failed_item.job is not None
    assert failed_item.job.status == "failed"
    assert failed_item.job.last_error is not None
    assert failed_item.job.last_error.code == "test_error"
    assert (queue.failed_dir / failed_item.filename).exists()


def test_enqueue_idempotent_across_states(tmp_path: Path):
    queue = FileQueue(tmp_path / "queue")
    now = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    job_done = _build_job("job-done", now, "run_done")
    job_failed = _build_job("job-failed", now + timedelta(minutes=1), "run_fail")

    assert queue.enqueue(job_done) is True
    assert queue.enqueue(job_failed) is True

    first = queue.dequeue_next()
    assert first is not None
    queue.mark_done(first)

    second = queue.dequeue_next()
    assert second is not None
    queue.mark_failed(second, JobError(code="test_error", message="fail"))

    # ห้าม enqueue ซ้ำ แม้งานจะอยู่ใน done/failed แล้ว
    assert queue.enqueue(job_done) is False
    assert queue.enqueue(job_failed) is False


def test_enqueue_dry_run_mode(tmp_path: Path):
    """
    ทดสอบ dry_run mode ของ enqueue

    dry_run=True ควรทำงานเหมือนปกติแต่ไม่เขียนไฟล์
    """

    queue = FileQueue(tmp_path / "queue")
    now = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    job = _build_job("job-001", now, "run_001")

    # dry_run ครั้งแรก ควรคืน True (งานยังไม่มี)
    assert queue.enqueue(job, dry_run=True) is True

    # ตรวจสอบว่าไม่มีไฟล์ถูกสร้าง
    pending = queue.list_pending()
    assert len(pending) == 0

    # dry_run อีกครั้ง ควรคืน True เพราะยังไม่มีไฟล์จริง
    assert queue.enqueue(job, dry_run=True) is True

    # enqueue จริง ควรคืน True
    assert queue.enqueue(job, dry_run=False) is True

    # ตรวจสอบว่ามีไฟล์ถูกสร้าง
    pending = queue.list_pending()
    assert len(pending) == 1
    assert pending[0].job_id == "job-001"

    # dry_run อีกครั้งหลังจาก enqueue แล้ว ควรคืน False
    assert queue.enqueue(job, dry_run=True) is False

    # enqueue จริงอีกครั้ง ก็ควรคืน False
    assert queue.enqueue(job, dry_run=False) is False
