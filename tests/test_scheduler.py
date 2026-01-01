"""ทดสอบการคัดเลือกงานตามแผนเวลา"""

import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path

from zoneinfo import ZoneInfo

from automation_core.queue import FileQueue
from automation_core.scheduler import schedule_due_jobs


def _utc_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


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


def test_scheduler_due_selection_deterministic(tmp_path):
    plan_path = tmp_path / "schedule_plan.yaml"
    _write_plan(plan_path)

    queue = FileQueue(tmp_path / "queue")
    now_utc = datetime(2026, 1, 1, 3, 0, tzinfo=timezone.utc)

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
    scheduled_utc = datetime(2026, 1, 1, 3, 0, tzinfo=timezone.utc)
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
