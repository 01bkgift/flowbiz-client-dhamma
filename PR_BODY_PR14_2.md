# PR14.2: Soft-Live Publish Mode (No-Public Safety)

## 🎯 Goal

Introduce a **Soft-Live** mode that acts as a safety layer for the pipeline. This mode allows the pipeline to run end-to-end (past approval gates) while **guaranteeing** that no content is made public. It enforces `dry_run` or `unlisted`/`private` modes at the infrastructure level, overriding any configuration that might attempt a public publish.

## 🛠 Model Changes

- **New Step:** `soft_live.enforce`
  - Validates `SOFT_LIVE_ENABLED` and `SOFT_LIVE_YOUTUBE_MODE` environment variables.
  - Produces `output/<run_id>/artifacts/soft_live_summary.json` as an audit trail.
  - Fail-closed behavior: Blocks execution if configuration is invalid (when `SOFT_LIVE_FAIL_CLOSED=true`).

- **Core Logic Enforcement:** `src/automation_core/youtube_upload.py`
  - Added direct logic to check `SOFT_LIVE_ENABLED` immediately before YouTube API calls.
  - **Force Override:** If Soft-Live is active, `privacy_status` is forced to match the safe mode (e.g., `unlisted`, `private`) or the upload is skipped entirely (`dry_run`).

- **Orchestrator:**
  - Registered `soft_live.enforce` agent.

- **Pipelines:**
  - Integrated `soft_live` step into `video_complete.yaml` and `youtube_upload_smoke_requires_quality.yaml`.
  - Placed strictly **after** `approval.gate` and **before** any publish/upload steps.

## 📋 Artifacts

- **Contracts:** `docs/contracts/soft_live_summary_v1.md`
- **Output:** `soft_live_summary.json`

## ✅ Verification

- **Unit Tests:** `tests/steps/soft_live_enforce/test_step.py`
  - Covered: Enabled (DryRun/Unlisted/Private), Disabled, Invalid Config, Fail-Closed.
  - Verified logic in `youtube_upload.py` using extensive mocking to ensure overrides happen.
- **Linting:** `ruff check` passed.

## 🔒 Security & Safety

- **ISO/SOC2 Compliance:**
  - **Segregation of Duties:** The enforcement logic is decoupled from the user input (YAML) and enforced by environment variables (Ops controlled).
  - **Audit Trail:** Every run produces a signed-off summary of the enforcement status.
  - **Fail-Safe:** Defaults to blocking if the safety mode cannot be determined.

## 🛑 Non-Goals

- No UI/Dashboard changes.
- No new external dependencies.
- No storage of secrets in artifacts.
