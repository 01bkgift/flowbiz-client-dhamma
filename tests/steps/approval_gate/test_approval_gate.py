import json
import os
from datetime import UTC, datetime, timedelta
from unittest import mock

import pytest

from steps.approval_gate import (
    ApprovalPendingHold,
    ApprovalRejectedError,
    run_approval_gate,
)


# Helpers
def _make_clock(start_time: datetime):
    current_time = start_time

    def clock():
        nonlocal current_time
        return current_time

    def advance(minutes=0, seconds=0):
        nonlocal current_time
        current_time += timedelta(minutes=minutes, seconds=seconds)

    return clock, advance


@pytest.fixture
def mock_clock():
    start = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
    return _make_clock(start)


@pytest.fixture
def run_dir(tmp_path):
    d = tmp_path / "run_001"
    d.mkdir()
    return d


@pytest.fixture
def step_config():
    return {"run_id": "run_001", "output": "approval_gate_summary.json"}


# --- Basic Flows ---
def test_disabled_approves_immediately(run_dir, step_config, mock_clock):
    clock, _ = mock_clock
    with mock.patch.dict(os.environ, {"APPROVAL_ENABLED": "false"}):
        path = run_approval_gate(step_config, run_dir, clock=clock)

    assert path.exists()
    data = json.loads(path.read_text())
    assert data["status"] == "approved_by_timeout"
    assert "GATING_BYPASSED" in data["reason_codes"]
    assert data["decision_source"] == "config"


def test_pending_within_grace_period(run_dir, step_config, mock_clock):
    clock, _ = mock_clock
    with mock.patch.dict(
        os.environ, {"APPROVAL_ENABLED": "true", "APPROVAL_GRACE_MINUTES": "60"}
    ):
        with pytest.raises(ApprovalPendingHold) as exc:
            run_approval_gate(step_config, run_dir, clock=clock)
        assert "Grace period active" in str(exc.value)

    # Verify artifact
    path = run_dir / "artifacts" / "approval_gate_summary.json"
    data = json.loads(path.read_text())
    assert data["status"] == "pending"
    assert data["evaluation_count"] == 1
    assert data["resolved_at_utc"].endswith("Z")  # Check ISO format with Z


def test_approved_after_grace_period(run_dir, step_config, mock_clock):
    clock, advance = mock_clock
    with mock.patch.dict(
        os.environ, {"APPROVAL_ENABLED": "true", "APPROVAL_GRACE_MINUTES": "60"}
    ):
        # First run: pending
        try:
            run_approval_gate(step_config, run_dir, clock=clock)
        except ApprovalPendingHold:
            pass

        # Advance time past grace
        advance(minutes=61)

        # Second run: approved
        path = run_approval_gate(step_config, run_dir, clock=clock)

    data = json.loads(path.read_text())
    assert data["status"] == "approved_by_timeout"
    assert data["evaluation_count"] == 2


def test_rejected_on_valid_cancel_file(run_dir, step_config, mock_clock):
    clock, _ = mock_clock
    # Create valid cancel file
    control_dir = run_dir / "control"
    control_dir.mkdir(parents=True, exist_ok=True)
    (control_dir / "cancel_publish.json").write_text(
        json.dumps(
            {"action": "cancel_publish", "actor": "admin", "reason": "bad content"}
        )
    )

    with mock.patch.dict(os.environ, {"APPROVAL_ENABLED": "true"}):
        with pytest.raises(ApprovalRejectedError):
            run_approval_gate(step_config, run_dir, clock=clock)

    path = run_dir / "artifacts" / "approval_gate_summary.json"
    data = json.loads(path.read_text())
    assert data["status"] == "rejected"
    assert data["human_actor"] == "admin"
    assert data["decision_source"] == "human"


# --- Failsafe Cases ---
def test_invalid_grace_minutes_failsafe_reject(run_dir, step_config, mock_clock):
    clock, _ = mock_clock
    with mock.patch.dict(
        os.environ,
        {"APPROVAL_ENABLED": "true", "APPROVAL_GRACE_MINUTES": "not-a-number"},
    ):
        with pytest.raises(ApprovalRejectedError):
            run_approval_gate(step_config, run_dir, clock=clock)

    path = run_dir / "artifacts" / "approval_gate_summary.json"
    data = json.loads(path.read_text())
    assert data["status"] == "rejected"
    assert "INVALID_CONFIG" in data["reason_codes"]


def test_cancel_file_missing_fields_failsafe_reject(run_dir, step_config, mock_clock):
    clock, _ = mock_clock
    control_dir = run_dir / "control"
    control_dir.mkdir(parents=True, exist_ok=True)
    # Missing actor/reason
    (control_dir / "cancel_publish.json").write_text(
        json.dumps(
            {
                "action": "cancel_publish"
                # missing actor/reason
            }
        )
    )

    with mock.patch.dict(os.environ, {"APPROVAL_ENABLED": "true"}):
        with pytest.raises(ApprovalRejectedError):
            run_approval_gate(step_config, run_dir, clock=clock)

    path = run_dir / "artifacts" / "approval_gate_summary.json"
    data = json.loads(path.read_text())
    assert data["status"] == "rejected"
    assert "CANCEL_FILE_INVALID" in data["reason_codes"]


def test_cancel_file_too_large_failsafe_reject(run_dir, step_config, mock_clock):
    clock, _ = mock_clock
    control_dir = run_dir / "control"
    control_dir.mkdir(parents=True, exist_ok=True)
    # Create large file > 4KB
    large_content = "x" * 5000
    (control_dir / "cancel_publish.json").write_text(
        json.dumps(
            {"action": "cancel_publish", "actor": "admin", "reason": large_content}
        )
    )

    with mock.patch.dict(os.environ, {"APPROVAL_ENABLED": "true"}):
        with pytest.raises(ApprovalRejectedError):
            run_approval_gate(step_config, run_dir, clock=clock)

    path = run_dir / "artifacts" / "approval_gate_summary.json"
    data = json.loads(path.read_text())
    assert "CANCEL_FILE_INVALID" in data["reason_codes"]


def test_cancel_file_invalid_json_failsafe_reject(run_dir, step_config, mock_clock):
    clock, _ = mock_clock
    control_dir = run_dir / "control"
    control_dir.mkdir(parents=True, exist_ok=True)
    (control_dir / "cancel_publish.json").write_text("{invalid_json")

    with mock.patch.dict(os.environ, {"APPROVAL_ENABLED": "true"}):
        with pytest.raises(ApprovalRejectedError):
            run_approval_gate(step_config, run_dir, clock=clock)

    path = run_dir / "artifacts" / "approval_gate_summary.json"
    data = json.loads(path.read_text())
    assert "CANCEL_FILE_INVALID" in data["reason_codes"]


# --- Idempotency Cases ---
def test_rerun_after_approved_preserves_state(run_dir, step_config, mock_clock):
    clock, advance = mock_clock

    # 1. Setup pre-approved state
    artifacts_dir = run_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    initial_summary = {
        "schema_version": "v1",
        "run_id": "run_001",
        "opened_at_utc": "2025-01-01T12:00:00Z",
        "resolved_at_utc": "2025-01-01T14:00:00Z",
        "status": "approved_by_timeout",
        "decision_source": "timeout",
        "grace_period_minutes": 120,
        "evaluation_count": 5,
        "reason_codes": [],
    }
    (artifacts_dir / "approval_gate_summary.json").write_text(
        json.dumps(initial_summary)
    )

    # 2. Run again (even if config changed to disable or whatever)
    with mock.patch.dict(os.environ, {"APPROVAL_ENABLED": "true"}):
        path = run_approval_gate(step_config, run_dir, clock=clock)

    data = json.loads(path.read_text())
    assert data["status"] == "approved_by_timeout"
    assert data["evaluation_count"] == 6  # incremented
    assert data["opened_at_utc"] == "2025-01-01T12:00:00Z"  # preserved


def test_rerun_after_rejected_preserves_state(run_dir, step_config, mock_clock):
    clock, _ = mock_clock
    artifacts_dir = run_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    initial_summary = {
        "schema_version": "v1",
        "run_id": "run_001",
        "opened_at_utc": "2025-01-01T12:00:00Z",
        "resolved_at_utc": "2025-01-01T12:05:00Z",
        "status": "rejected",
        "decision_source": "human",
        "grace_period_minutes": 120,
        "evaluation_count": 2,
        "reason_codes": [],
        "human_action": "cancel_publish",
        "human_actor": "admin",
        "human_reason": "bad",
    }
    (artifacts_dir / "approval_gate_summary.json").write_text(
        json.dumps(initial_summary)
    )

    with mock.patch.dict(os.environ, {"APPROVAL_ENABLED": "true"}):
        with pytest.raises(ApprovalRejectedError):
            run_approval_gate(step_config, run_dir, clock=clock)

    data = json.loads((artifacts_dir / "approval_gate_summary.json").read_text())
    assert data["status"] == "rejected"
    assert data["evaluation_count"] == 3


def test_opened_at_persists_across_reruns(run_dir, step_config, mock_clock):
    clock, advance = mock_clock
    with mock.patch.dict(os.environ, {"APPROVAL_ENABLED": "true"}):
        # Run 1
        try:
            run_approval_gate(step_config, run_dir, clock=clock)
        except ApprovalPendingHold:
            pass

        path = run_dir / "artifacts" / "approval_gate_summary.json"
        t1 = json.loads(path.read_text())["opened_at_utc"]

        advance(minutes=10)

        # Run 2
        try:
            run_approval_gate(step_config, run_dir, clock=clock)
        except ApprovalPendingHold:
            pass

        t2 = json.loads(path.read_text())["opened_at_utc"]

        assert t1 == t2  # Must be identical


def test_evaluation_count_increments(run_dir, step_config, mock_clock):
    # Implicitly tested above, but explicit check
    clock, _ = mock_clock
    with mock.patch.dict(os.environ, {"APPROVAL_ENABLED": "true"}):
        try:
            run_approval_gate(step_config, run_dir, clock=clock)
        except ApprovalPendingHold:
            pass

        try:
            run_approval_gate(step_config, run_dir, clock=clock)
        except ApprovalPendingHold:
            pass

    path = run_dir / "artifacts" / "approval_gate_summary.json"
    assert json.loads(path.read_text())["evaluation_count"] == 2


# --- Priority Order Cases ---
def test_cancel_file_takes_priority_over_timeout(run_dir, step_config, mock_clock):
    clock, advance = mock_clock
    # Setup: Grace period expired AND cancel file exists
    # If timeout logic checked first -> approved
    # If cancel checked first -> rejected

    # 1. Run 1 to open gate
    with mock.patch.dict(
        os.environ, {"APPROVAL_ENABLED": "true", "APPROVAL_GRACE_MINUTES": "60"}
    ):
        try:
            run_approval_gate(step_config, run_dir, clock=clock)
        except ApprovalPendingHold:
            pass

    # 2. Add cancel file
    control_dir = run_dir / "control"
    control_dir.mkdir(parents=True, exist_ok=True)
    (control_dir / "cancel_publish.json").write_text(
        json.dumps({"action": "cancel_publish", "actor": "admin", "reason": "bad"})
    )

    # 3. Advance time past grace
    advance(minutes=61)

    # 4. Run 2
    with mock.patch.dict(
        os.environ, {"APPROVAL_ENABLED": "true", "APPROVAL_GRACE_MINUTES": "60"}
    ):
        with pytest.raises(ApprovalRejectedError):
            run_approval_gate(step_config, run_dir, clock=clock)

    path = run_dir / "artifacts" / "approval_gate_summary.json"
    data = json.loads(path.read_text())
    assert data["status"] == "rejected"  # Correct priority
    assert data["decision_source"] == "human"


def test_terminal_state_wins_over_config_change(run_dir, step_config, mock_clock):
    clock, advance = mock_clock
    # 1. Setup rejected state
    artifacts_dir = run_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    rejected_summary = {
        "schema_version": "v1",
        "run_id": "run_999",
        "opened_at_utc": "2025-01-01T12:00:00Z",
        "resolved_at_utc": "2025-01-01T12:05:00Z",
        "status": "rejected",
        "decision_source": "human",
        "grace_period_minutes": 120,
        "evaluation_count": 1,
        "reason_codes": [],
        "human_action": "cancel_publish",
        "human_actor": "admin",
        "human_reason": "stop",
    }
    (artifacts_dir / "approval_gate_summary.json").write_text(
        json.dumps(rejected_summary)
    )

    # 2. Run with gating DISABLED (should normally approve)
    # BUT existing state is rejected (terminal), so it should stay rejected
    with mock.patch.dict(os.environ, {"APPROVAL_ENABLED": "false"}):
        with pytest.raises(ApprovalRejectedError):
            run_approval_gate(step_config, run_dir, clock=clock)

    # Verify artifact unchanged except count
    path = run_dir / "artifacts" / "approval_gate_summary.json"
    data = json.loads(path.read_text())
    assert data["status"] == "rejected"
    assert data["evaluation_count"] == 2
