from __future__ import annotations

import json
import os
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from .model import (
    ApprovalGateSummary,
    CancelPublishAction,
    DecisionSourceEnum,
    StatusEnum,
)


# Exception Classes for Orchestrator Control
class ApprovalPendingHold(Exception):
    """Raised when approval is still pending. Pipeline should retry later."""

    pass


class ApprovalRejectedError(Exception):
    """Raised when approval is rejected. Pipeline must not continue."""

    pass


def _get_utc_now() -> datetime:
    return datetime.now(UTC)


def run_approval_gate(
    step: dict[str, Any],
    run_dir: Path,
    clock: Callable[[], datetime] = _get_utc_now,
) -> Path:
    """
    Approval Gate Step Implementation

    Deterministic gate that blocks pipeline until grace period expires or user cancels.
    """
    # 1. Setup paths
    run_id = step.get("run_id")
    if not run_id:
        # Fallback if run_id not in step config (usually injected by orchestrator)
        run_id = run_dir.name

    control_dir = run_dir / "control"
    artifacts_dir = run_dir / "artifacts"

    # Atomic directory creation
    os.makedirs(control_dir, exist_ok=True)
    os.makedirs(artifacts_dir, exist_ok=True)

    summary_path = artifacts_dir / "approval_gate_summary.json"
    cancel_file_path = control_dir / "cancel_publish.json"

    # 2. Get Current Time
    now_utc = clock()
    now_iso = now_utc.isoformat().replace("+00:00", "Z")

    # 3. Read Config
    env_enabled = os.environ.get("APPROVAL_ENABLED", "true")
    env_grace = os.environ.get("APPROVAL_GRACE_MINUTES", "120")

    # Initialize variables
    status: StatusEnum
    decision_source: DecisionSourceEnum
    reason_codes: list[str] = []
    human_action = None
    human_actor = None
    human_reason = None

    # --- PRIORITY 1: CHECK EXISTING TERMINAL STATE (Idempotency) ---
    # Governance: Terminal state (REJECTED/APPROVED) always wins over config changes.
    existing_artifact: ApprovalGateSummary | None = None
    if summary_path.exists():
        try:
            data = json.loads(summary_path.read_text(encoding="utf-8"))
            existing_artifact = ApprovalGateSummary(**data)
        except Exception:
            # Corrupt artifact -> ignore and treat as fresh run
            pass

    if existing_artifact and existing_artifact.status in [
        StatusEnum.APPROVED_BY_TIMEOUT,
        StatusEnum.REJECTED,
    ]:
        # Return same result as stored => INCREMENT evaluation_count only
        updated_summary = existing_artifact.model_copy(
            update={
                "evaluation_count": existing_artifact.evaluation_count + 1,
                "resolved_at_utc": now_iso,
            }
        )
        summary_path.write_text(
            updated_summary.model_dump_json(indent=2), encoding="utf-8"
        )

        if updated_summary.status == StatusEnum.REJECTED:
            # Re-raise rejection to keep blocking
            reason = (
                " ".join(updated_summary.reason_codes) or updated_summary.human_reason
            )
            raise ApprovalRejectedError(f"Approval previously rejected: {reason}")

        return summary_path

    # --- PRIORITY 2: CHECK GATING ENABLED ---
    if env_enabled != "true":
        status = StatusEnum.APPROVED_BY_TIMEOUT
        decision_source = DecisionSourceEnum.CONFIG
        reason_codes.append("GATING_BYPASSED")

        opened_at = now_iso
        if existing_artifact:
            opened_at = existing_artifact.opened_at_utc
            eval_count = existing_artifact.evaluation_count + 1
        else:
            eval_count = 1

        try:
            grace_int = int(env_grace)
        except Exception:
            grace_int = 120

        summary = ApprovalGateSummary(
            run_id=run_id,
            opened_at_utc=opened_at,
            resolved_at_utc=now_iso,
            status=StatusEnum.APPROVED_BY_TIMEOUT,
            decision_source=DecisionSourceEnum.CONFIG,
            grace_period_minutes=grace_int,
            reason_codes=["GATING_BYPASSED"],
            evaluation_count=eval_count,
        )
        summary_path.write_text(summary.model_dump_json(indent=2), encoding="utf-8")
        return summary_path

    # From here on, Gating is ENABLED and no terminal state exists.

    # Prepare for active evaluation
    # Determine opened_at
    if existing_artifact:
        opened_at_iso = existing_artifact.opened_at_utc
        # Parse for calculation
        # opened_at is ISO string. Convert back to datetime for math.
        # Assuming Z suffix from our code.
        try:
            if opened_at_iso.endswith("Z"):
                opened_at_dt = datetime.fromisoformat(opened_at_iso[:-1]).replace(
                    tzinfo=UTC
                )
            else:
                opened_at_dt = datetime.fromisoformat(opened_at_iso)
        except ValueError:
            # Corrupt timestamp? Failsafe
            status = StatusEnum.REJECTED
            decision_source = DecisionSourceEnum.FAILSAFE
            reason_codes = ["FAILSAFE_REJECT", "INVALID_TIMESTAMP"]
            raise ApprovalRejectedError(
                "Invalid opened_at timestamp in artifact"
            ) from None

        eval_count = existing_artifact.evaluation_count + 1
    else:
        opened_at_iso = now_iso
        opened_at_dt = now_utc
        eval_count = 1

    # Initialize common artifact fields
    # We will finalize these before matching logic
    config_grace_minutes: int

    try:
        # Priority 4: CHECK CONFIG VALIDITY
        config_grace_minutes = int(env_grace)
        if not (1 <= config_grace_minutes <= 1440):
            raise ValueError("Value must be between 1 and 1440.")

    except ValueError as e:
        # Failsafe Reject
        summary = ApprovalGateSummary(
            run_id=run_id,
            opened_at_utc=opened_at_iso,
            resolved_at_utc=now_iso,
            status=StatusEnum.REJECTED,
            decision_source=DecisionSourceEnum.FAILSAFE,
            grace_period_minutes=0,  # Placeholder
            reason_codes=["INVALID_CONFIG", "FAILSAFE_REJECT"],
            evaluation_count=eval_count,
        )
        summary_path.write_text(summary.model_dump_json(indent=2), encoding="utf-8")
        raise ApprovalRejectedError(f"Invalid APPROVAL_GRACE_MINUTES: {e}") from None

    # Priority 3: CHECK CANCEL FILE
    if cancel_file_path.exists():
        try:
            # Validation Rules
            stat = cancel_file_path.stat()
            if stat.st_size > 4096:  # 4KB
                raise ValueError("File too large")

            content = cancel_file_path.read_text(encoding="utf-8")
            data = json.loads(content)

            # Validate schema via Pydantic
            action = CancelPublishAction(**data)

            # Valid Cancel
            status = StatusEnum.REJECTED
            decision_source = DecisionSourceEnum.HUMAN
            human_action = action.action
            human_actor = action.actor
            human_reason = action.reason

            summary = ApprovalGateSummary(
                run_id=run_id,
                opened_at_utc=opened_at_iso,
                resolved_at_utc=now_iso,
                status=status,
                decision_source=decision_source,
                grace_period_minutes=config_grace_minutes,
                human_action=human_action,
                human_actor=human_actor,
                human_reason=human_reason,
                reason_codes=[],
                evaluation_count=eval_count,
            )
            summary_path.write_text(summary.model_dump_json(indent=2), encoding="utf-8")

        except Exception as e:
            # Partial write, invalid json, schema fail, size fail
            status = StatusEnum.REJECTED
            decision_source = DecisionSourceEnum.FAILSAFE
            reason_codes = ["CANCEL_FILE_INVALID", "FAILSAFE_REJECT"]

            summary = ApprovalGateSummary(
                run_id=run_id,
                opened_at_utc=opened_at_iso,
                resolved_at_utc=now_iso,
                status=status,
                decision_source=decision_source,
                grace_period_minutes=config_grace_minutes,
                reason_codes=reason_codes,
                evaluation_count=eval_count,
            )
            summary_path.write_text(summary.model_dump_json(indent=2), encoding="utf-8")
            raise ApprovalRejectedError(f"Invalid cancel file: {e}") from e

        raise ApprovalRejectedError(
            f"Rejected by human: {human_actor} - {human_reason}"
        )

    # Priority 5: CHECK GRACE PERIOD
    expiration_time = opened_at_dt + timedelta(minutes=config_grace_minutes)

    if now_utc >= expiration_time:
        # Timeout -> Approve
        status = StatusEnum.APPROVED_BY_TIMEOUT
        decision_source = DecisionSourceEnum.TIMEOUT

        summary = ApprovalGateSummary(
            run_id=run_id,
            opened_at_utc=opened_at_iso,
            resolved_at_utc=now_iso,
            status=status,
            decision_source=decision_source,
            grace_period_minutes=config_grace_minutes,
            evaluation_count=eval_count,
        )
        summary_path.write_text(summary.model_dump_json(indent=2), encoding="utf-8")
        return summary_path

    else:
        # Pending
        status = StatusEnum.PENDING
        decision_source = DecisionSourceEnum.TIMEOUT

        summary = ApprovalGateSummary(
            run_id=run_id,
            opened_at_utc=opened_at_iso,
            resolved_at_utc=now_iso,
            status=status,
            decision_source=decision_source,
            grace_period_minutes=config_grace_minutes,
            evaluation_count=eval_count,
        )
        summary_path.write_text(summary.model_dump_json(indent=2), encoding="utf-8")

        wait_mins = round((expiration_time - now_utc).total_seconds() / 60, 1)
        raise ApprovalPendingHold(
            f"Approval pending. Grace period active for another {wait_mins} minutes."
        )
