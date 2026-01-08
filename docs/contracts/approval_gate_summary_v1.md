# Approval Gate Summary v1

**Artifact:** `approval_gate_summary.json`
**Step:** `approval.gate` (ApprovalGateStep)
**Generated:** Always (even if failed/rejected)

## Purpose

Acts as a deterministic firewall for the publishing pipeline. It allows a "grace period" (default 2 hours) for human intervention before auto-approving content. If a human explicitly cancels via file drop, the pipeline halts permanently.

## Schema `v1`

| Field | Type | Description |
|---|---|---|
| `schema_version` | string | Constant `"v1"` |
| `run_id` | string | Pipeline run identifier |
| `opened_at_utc` | string | ISO8601 timestamp when gate was FIRST opened |
| `resolved_at_utc` | string | ISO8601 timestamp of LATEST evaluation |
| `status` | enum | `pending` \| `approved_by_timeout` \| `rejected` |
| `decision_source` | enum | `human` \| `timeout` \| `config` \| `failsafe` |
| `grace_period_minutes` | int | Configured grace window in minutes |
| `human_action` | string? | `"cancel_publish"` if decision_source=human |
| `human_actor` | string? | Name of actor who cancelled |
| `human_reason` | string? | Reason for cancellation |
| `reason_codes` | list[str] | Machine readable codes (e.g. `CANCEL_FILE_INVALID`) |
| `evaluation_count` | int | Number of times this gate has been checked |

## Status Values

- **pending**: Grace period is active. Pipeline raises `ApprovalPendingHold` (temporary fail).
- **approved_by_timeout**: Grace period expired with no cancel file (OR disabled via config). Pipeline proceeds.
- **rejected**: Human cancelled OR fatal error (failsafe). Pipeline raises `ApprovalRejectedError` (permanent fail).

## Control File (To Cancel)

Place file at: `output/<run_id>/control/cancel_publish.json`

```json
{
  "action": "cancel_publish",
  "actor": "AdminUser",
  "reason": "Content violates policy on politics"
}
```

## Example (Approved)

```json
{
  "schema_version": "v1",
  "run_id": "run_123",
  "opened_at_utc": "2025-01-08T10:00:00Z",
  "resolved_at_utc": "2025-01-08T12:05:00Z",
  "status": "approved_by_timeout",
  "decision_source": "timeout",
  "grace_period_minutes": 120,
  "evaluation_count": 5
}
```

## Example (Rejected)

```json
{
  "schema_version": "v1",
  "run_id": "run_123",
  "opened_at_utc": "2025-01-08T10:00:00Z",
  "resolved_at_utc": "2025-01-08T10:30:00Z",
  "status": "rejected",
  "decision_source": "human",
  "human_action": "cancel_publish",
  "human_actor": "Editor",
  "human_reason": "Typo in title",
  "evaluation_count": 2
}
```
