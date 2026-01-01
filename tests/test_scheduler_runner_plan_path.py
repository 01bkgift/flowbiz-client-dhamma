"""ทดสอบสัญญา plan_path ของ scheduler runner

เป้าหมาย:
- สัญญาใน BASELINE กำหนดว่า plan_path ต้องไม่เป็น absolute
- หากผู้ใช้ส่ง --plan เป็น absolute path ให้ runner ทำเป็น plan_parse_error
  และเขียน summary โดย plan_path เป็น "" (ไม่หลุด absolute)
"""

from __future__ import annotations

import importlib.util
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType

import pytest


def _load_runner() -> ModuleType:
    runner_path = Path(__file__).parent.parent / "scripts" / "scheduler_runner.py"
    spec = importlib.util.spec_from_file_location("scheduler_runner", runner_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_schedule_rejects_absolute_plan_path_and_redacts_in_summary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = _load_runner()
    monkeypatch.setenv("PIPELINE_ENABLED", "true")
    monkeypatch.setenv("SCHEDULER_ENABLED", "true")

    absolute_plan = (tmp_path / "schedule_plan.yaml").resolve()
    absolute_plan.write_text(
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

    now_utc = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    summary = runner.run_schedule(
        plan_path=absolute_plan,
        queue_dir=tmp_path / "queue",
        now=now_utc,
        window_minutes=10,
        dry_run=False,
        base_dir=tmp_path,
    )

    assert summary is not None
    assert summary["plan_path"] == ""
    assert summary["skipped_entries"][0]["code"] == "plan_parse_error"

    # ต้องไม่หลุด absolute path ไปอยู่ใน summary
    assert str(absolute_plan).replace("\\", "/") not in str(summary)

    # และยังต้องมี artifact ถูกเขียนออกมา
    artifacts_dir = tmp_path / "output" / "scheduler" / "artifacts"
    assert artifacts_dir.exists()
    assert list(artifacts_dir.glob("schedule_summary_*.json"))
