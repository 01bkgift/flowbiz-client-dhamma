# PR14.1: Approval Gate Implementation

## Summary

Implements a strict **Approval Gate** step (`approval.gate`) in the publishing pipeline. This step acts as a firewall, enforcing a configurable grace period (default 120 minutes) before allowing any content to be published. It supports auto-approval by timeout or explicit rejection via a control file.

## Key Changes

### New Step: `approval.gate`

- **Location**: `src/steps/approval_gate/`
- **Logic**:
  1. Checks `APPROVAL_ENABLED` (Config Priority).
  2. Checks existing artifact for idempotency (State Priority).
  3. Checks `output/<run_id>/control/cancel_publish.json` for manual stop decision (Human Priority).
  4. Checks if `APPROVAL_GRACE_MINUTES` has passed (Time Priority).
- **Outputs**: `approval_gate_summary.json` (v1 schema).

### Pipeline Updates

- **`video_complete.yaml`**: Inserted `approval_gate` after `decision_support`.
- **`youtube_upload_smoke_requires_quality.yaml`**: Inserted `approval_gate` before `youtube_upload`.
- **Orchestrator**: Registered new step in `AGENTS` registry.

### Contracts

- Defined strict artifact schema in `src/steps/approval_gate/model.py`.
- Documented behavior in `docs/contracts/approval_gate_summary_v1.md`.

## Verification

- **Unit Tests**: Added 14 comprehensive test cases in `tests/steps/approval_gate/test_step.py` covering all logic branches, failsafes, and race conditions.
- **Manual Verification**: Verified via `walkthrough.md` (Artifact).

## Checklist

- [x] Implementation (Source + Tests)
- [x] Pipeline Integration
- [x] Contract Documentation
- [x] Pass `pytest`
- [x] Pass `ruff check` & `ruff format`
