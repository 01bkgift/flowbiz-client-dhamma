"""ทดสอบการทำงานของ worker runner"""

import importlib.util
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType

import pytest

from automation_core.queue import FileQueue, JobSpec


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


def _load_runner() -> ModuleType:
    runner_path = Path(__file__).parent.parent / "scripts" / "scheduler_runner.py"
    spec = importlib.util.spec_from_file_location("scheduler_runner", runner_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture(autouse=True)
def _set_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("YOUTUBE_UPLOAD_ENABLED", "false")


def test_worker_queue_empty(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runner = _load_runner()
    monkeypatch.setenv("PIPELINE_ENABLED", "true")
    monkeypatch.setenv("WORKER_ENABLED", "true")

    summary = runner.run_worker(
        queue_dir=tmp_path / "queue",
        dry_run=False,
        base_dir=tmp_path,
        pipeline_runner=lambda *_args: None,
    )

    assert summary is not None
    assert summary["decision"] == "skipped"
    assert summary["error"]["code"] == "queue_empty"
    assert (tmp_path / "output" / "worker" / "artifacts").exists()


def test_worker_dry_run_no_orchestrator(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = _load_runner()
    monkeypatch.setenv("PIPELINE_ENABLED", "true")
    monkeypatch.setenv("WORKER_ENABLED", "false")

    queue = FileQueue(tmp_path / "queue")
    job = _build_job("job-dry", datetime(2026, 1, 1, 0, 0, tzinfo=UTC), "run1")
    queue.enqueue(job)

    called = {"count": 0}

    def _runner_stub(*_args):
        called["count"] += 1

    summary = runner.run_worker(
        queue_dir=tmp_path / "queue",
        dry_run=True,
        base_dir=tmp_path,
        pipeline_runner=_runner_stub,
    )

    assert summary is not None
    assert summary["dry_run"] is True
    assert summary["decision"] == "skipped"
    assert called["count"] == 0
    assert len(queue.list_pending()) == 1


def test_worker_runs_once(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runner = _load_runner()
    monkeypatch.setenv("PIPELINE_ENABLED", "true")
    monkeypatch.setenv("WORKER_ENABLED", "true")

    queue = FileQueue(tmp_path / "queue")
    job = _build_job(
        "job-run",
        datetime(2026, 1, 1, 0, 0, tzinfo=UTC),
        "run2",
    )
    queue.enqueue(job)

    called = {"count": 0}

    def _runner_stub(*_args):
        called["count"] += 1

    summary = runner.run_worker(
        queue_dir=tmp_path / "queue",
        dry_run=False,
        base_dir=tmp_path,
        pipeline_runner=_runner_stub,
    )

    assert summary is not None
    assert summary["decision"] == "done"
    assert called["count"] == 1
    assert len(queue.list_pending()) == 0
    assert list(queue.done_dir.glob("*.json"))


def test_pipeline_disabled_no_side_effects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = _load_runner()
    monkeypatch.setenv("PIPELINE_ENABLED", "false")
    monkeypatch.setenv("WORKER_ENABLED", "true")
    monkeypatch.setenv("SCHEDULER_ENABLED", "true")

    worker_summary = runner.run_worker(
        queue_dir=tmp_path / "queue",
        dry_run=False,
        base_dir=tmp_path,
        pipeline_runner=lambda *_args: None,
    )
    scheduler_summary = runner.run_schedule(
        plan_path=tmp_path / "schedule_plan.yaml",
        queue_dir=tmp_path / "queue",
        now=None,
        window_minutes=10,
        dry_run=False,
        base_dir=tmp_path,
    )

    assert worker_summary is None
    assert scheduler_summary is None
    assert not (tmp_path / "output").exists()


def test_worker_rejects_pipeline_path_outside_base_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = _load_runner()
    monkeypatch.setenv("PIPELINE_ENABLED", "true")
    monkeypatch.setenv("WORKER_ENABLED", "true")

    queue = FileQueue(tmp_path / "queue")
    job = _build_job(
        "job-bad-path",
        datetime(2026, 1, 1, 0, 0, tzinfo=UTC),
        "run_bad",
    ).model_copy(update={"pipeline_path": "../outside.yml"})
    queue.enqueue(job)

    called = {"count": 0}

    def _runner_stub(*_args):
        called["count"] += 1

    summary = runner.run_worker(
        queue_dir=tmp_path / "queue",
        dry_run=False,
        base_dir=tmp_path,
        pipeline_runner=_runner_stub,
    )

    assert summary is not None
    assert summary["decision"] == "failed"
    assert summary["error"]["code"] == "orchestrator_failed"
    assert called["count"] == 0
    assert list(queue.failed_dir.glob("*.json"))
