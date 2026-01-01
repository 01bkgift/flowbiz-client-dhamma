"""ทดสอบการคัดเลือกงานตามแผนเวลา"""

import hashlib
from datetime import UTC, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from automation_core.queue import FileQueue
from automation_core.scheduler import SchedulePlanError, schedule_due_jobs


def _utc_iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _write_plan(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                'schema_version: "v1"',
                'timezone: "Asia/Bangkok"',
                "entries:",
                '  - publish_at: "2026-01-01T10:00"',
                '    pipeline_path: "pipeline.web.yml"',
                '  - publish_at: "2026-01-01T10:05+07:00"',
                '    pipeline_path: "pipeline.web.yml"',
                '    run_id_prefix: "mid_morning"',
                '  - publish_at: "2026-01-01T10:30"',
                '    pipeline_path: "pipeline.web.yml"',
            ]
        ),
        encoding="utf-8",
    )


def test_scheduler_due_selection_deterministic(tmp_path: Path):
    plan_path = tmp_path / "schedule_plan.yaml"
    _write_plan(plan_path)

    queue = FileQueue(tmp_path / "queue")
    now_utc = datetime(2026, 1, 1, 3, 0, tzinfo=UTC)

    result = schedule_due_jobs(
        plan_path=plan_path,
        queue=queue,
        now_utc=now_utc,
        window_minutes=10,
        dry_run=True,
        scheduler_enabled=True,
        created_at_utc=now_utc,
    )

    assert len(result.enqueued_job_ids) == 2
    assert any(skip.code == "entry_not_due" for skip in result.skipped_entries)

    tz = ZoneInfo("Asia/Bangkok")
    scheduled_utc = datetime(2026, 1, 1, 3, 0, tzinfo=UTC)
    run_id_base = scheduled_utc.astimezone(tz).strftime("%Y%m%d_%H%M")
    seed = f"{_utc_iso(scheduled_utc)}|pipeline.web.yml|{run_id_base}"
    expected_job_id = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12]

    assert result.enqueued_job_ids[0] == expected_job_id

    repeat = schedule_due_jobs(
        plan_path=plan_path,
        queue=queue,
        now_utc=now_utc,
        window_minutes=10,
        dry_run=True,
        scheduler_enabled=True,
        created_at_utc=now_utc + timedelta(minutes=1),
    )
    assert repeat.enqueued_job_ids == result.enqueued_job_ids


def test_scheduler_invalid_timezone(tmp_path: Path):
    """ทดสอบการจัดการ timezone ที่ไม่ถูกต้อง"""
    plan_path = tmp_path / "schedule_plan.yaml"
    plan_path.write_text(
        "\n".join(
            [
                'schema_version: "v1"',
                'timezone: "Invalid/Timezone"',
                "entries:",
                '  - publish_at: "2026-01-01T10:00"',
                '    pipeline_path: "pipeline.web.yml"',
            ]
        ),
        encoding="utf-8",
    )

    queue = FileQueue(tmp_path / "queue")
    now_utc = datetime(2026, 1, 1, 3, 0, tzinfo=UTC)

    with pytest.raises(SchedulePlanError):
        schedule_due_jobs(
            plan_path=plan_path,
            queue=queue,
            now_utc=now_utc,
            window_minutes=10,
            dry_run=True,
            scheduler_enabled=True,
            created_at_utc=now_utc,
        )


def test_scheduler_invalid_publish_at(tmp_path: Path):
    """ทดสอบการจัดการรูปแบบ publish_at ที่ไม่ถูกต้อง"""
    plan_path = tmp_path / "schedule_plan.yaml"
    plan_path.write_text(
        "\n".join(
            [
                'schema_version: "v1"',
                'timezone: "Asia/Bangkok"',
                "entries:",
                '  - publish_at: "invalid-datetime"',
                '    pipeline_path: "pipeline.web.yml"',
            ]
        ),
        encoding="utf-8",
    )

    queue = FileQueue(tmp_path / "queue")
    now_utc = datetime(2026, 1, 1, 3, 0, tzinfo=UTC)

    result = schedule_due_jobs(
        plan_path=plan_path,
        queue=queue,
        now_utc=now_utc,
        window_minutes=10,
        dry_run=True,
        scheduler_enabled=True,
        created_at_utc=now_utc,
    )

    # ควรจะข้ามงานที่มี publish_at ไม่ถูกต้อง
    assert len(result.enqueued_job_ids) == 0
    assert len(result.skipped_entries) == 1
    assert result.skipped_entries[0].code == "job_invalid"


def test_scheduler_missing_required_fields(tmp_path: Path):
    """ทดสอบการจัดการเมื่อขาดฟิลด์ที่จำเป็น"""
    plan_path = tmp_path / "schedule_plan.yaml"
    plan_path.write_text(
        "\n".join(
            [
                'schema_version: "v1"',
                'timezone: "Asia/Bangkok"',
                "entries:",
                '  - publish_at: "2026-01-01T10:00"',
                # ขาด pipeline_path
            ]
        ),
        encoding="utf-8",
    )

    queue = FileQueue(tmp_path / "queue")
    now_utc = datetime(2026, 1, 1, 3, 0, tzinfo=UTC)

    result = schedule_due_jobs(
        plan_path=plan_path,
        queue=queue,
        now_utc=now_utc,
        window_minutes=10,
        dry_run=True,
        scheduler_enabled=True,
        created_at_utc=now_utc,
    )

    # ควรจะข้ามงานที่ขาดฟิลด์จำเป็น
    assert len(result.enqueued_job_ids) == 0
    assert len(result.skipped_entries) == 1
    assert result.skipped_entries[0].code == "job_invalid"


def test_scheduler_malformed_yaml(tmp_path: Path):
    """ทดสอบการจัดการ YAML ที่ไม่ถูกต้อง"""
    plan_path = tmp_path / "schedule_plan.yaml"
    plan_path.write_text("invalid: yaml: [content", encoding="utf-8")

    queue = FileQueue(tmp_path / "queue")
    now_utc = datetime(2026, 1, 1, 3, 0, tzinfo=UTC)

    with pytest.raises(SchedulePlanError):
        schedule_due_jobs(
            plan_path=plan_path,
            queue=queue,
            now_utc=now_utc,
            window_minutes=10,
            dry_run=True,
            scheduler_enabled=True,
            created_at_utc=now_utc,
        )


@pytest.mark.parametrize(
    "pipeline_path",
    [
        "../pipeline.web.yml",
        "/abs/pipeline.web.yml",
    ],
)
def test_scheduler_rejects_pipeline_path_traversal(tmp_path: Path, pipeline_path: str):
    """ทดสอบว่า ScheduleEntry ปฏิเสธ path traversal/absolute path"""

    plan_path = tmp_path / "schedule_plan.yaml"
    plan_path.write_text(
        "\n".join(
            [
                'schema_version: "v1"',
                'timezone: "Asia/Bangkok"',
                "entries:",
                '  - publish_at: "2026-01-01T10:00"',
                f'    pipeline_path: "{pipeline_path}"',
            ]
        ),
        encoding="utf-8",
    )

    queue = FileQueue(tmp_path / "queue")
    now_utc = datetime(2026, 1, 1, 3, 0, tzinfo=UTC)

    result = schedule_due_jobs(
        plan_path=plan_path,
        queue=queue,
        now_utc=now_utc,
        window_minutes=10,
        dry_run=True,
        scheduler_enabled=True,
        created_at_utc=now_utc,
    )

    assert result.enqueued_job_ids == []
    assert len(result.skipped_entries) == 1
    assert result.skipped_entries[0].code == "job_invalid"


def test_scheduler_dry_run_matches_actual_run(tmp_path: Path):
    """
    ทดสอบว่า dry_run ให้ผลลัพธ์ที่ตรงกับ actual run

    ก่อนหน้านี้ dry_run ใช้ exists() แยกจาก enqueue() ทำให้มี race condition
    ตอนนี้ใช้ enqueue() แบบเดียวกันทั้งสองโหมด
    """

    plan_path = tmp_path / "schedule_plan.yaml"
    plan_path.write_text(
        "\n".join(
            [
                'schema_version: "v1"',
                'timezone: "Asia/Bangkok"',
                "entries:",
                '  - publish_at: "2026-01-01T10:00"',
                '    pipeline_path: "pipeline.web.yml"',
            ]
        ),
        encoding="utf-8",
    )

    queue = FileQueue(tmp_path / "queue")
    now_utc = datetime(2026, 1, 1, 3, 0, tzinfo=UTC)

    # Run 1: dry_run ครั้งแรก ควรบอกว่าจะ enqueue
    result1 = schedule_due_jobs(
        plan_path=plan_path,
        queue=queue,
        now_utc=now_utc,
        window_minutes=10,
        dry_run=True,
        scheduler_enabled=True,
        created_at_utc=now_utc,
    )

    assert len(result1.enqueued_job_ids) == 1
    assert len(result1.skipped_entries) == 0
    job_id = result1.enqueued_job_ids[0]

    # Run 2: actual run ควร enqueue งานจริง
    result2 = schedule_due_jobs(
        plan_path=plan_path,
        queue=queue,
        now_utc=now_utc,
        window_minutes=10,
        dry_run=False,
        scheduler_enabled=True,
        created_at_utc=now_utc,
    )

    assert result2.enqueued_job_ids == [job_id]
    assert len(result2.skipped_entries) == 0

    # Run 3: dry_run อีกครั้งหลังจาก enqueue แล้ว ควรบอกว่า skip
    result3 = schedule_due_jobs(
        plan_path=plan_path,
        queue=queue,
        now_utc=now_utc,
        window_minutes=10,
        dry_run=True,
        scheduler_enabled=True,
        created_at_utc=now_utc,
    )

    assert len(result3.enqueued_job_ids) == 0
    assert len(result3.skipped_entries) == 1
    assert result3.skipped_entries[0].code == "already_enqueued"

    # Run 4: actual run อีกครั้ง ก็ควร skip เหมือนกัน
    result4 = schedule_due_jobs(
        plan_path=plan_path,
        queue=queue,
        now_utc=now_utc,
        window_minutes=10,
        dry_run=False,
        scheduler_enabled=True,
        created_at_utc=now_utc,
    )

    assert len(result4.enqueued_job_ids) == 0
    assert len(result4.skipped_entries) == 1
    assert result4.skipped_entries[0].code == "already_enqueued"
