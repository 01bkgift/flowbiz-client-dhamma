# Decision Support Summary v1

**Artifact:** `decision_support_summary.json`
**Step:** `decision.support` (DecisionSupportStep)
**Generated:** Always (even if inputs missing)

## Purpose

Provides a deterministic, read-only recommendation for the operator on whether to publish, hold, or edit content. It aggregates signals from Quality Gate and KPI trends.

## Schema `v1`

| Field | Type | Description |
|---|---|---|
| `schema_version` | string | Constant `"v1"` |
| `generated_at` | string | ISO8601 timestamp of generation |
| `run_id` | string | Pipeline run identifier |
| `decision` | enum | `recommend_publish` \| `recommend_hold` \| `recommend_edit` |
| `confidence` | float | 0.0 - 1.0 (Rule-based confidence) |
| `reasons` | list[str] | List of reason codes (e.g., `"QUALITY_FAIL"`, `"KPI_UP"`) |
| `recommendations` | list[str] | Human-readable bullet points for the operator |
| `inputs_used` | dict | Map of artifact key to path (e.g., `quality_gate`, `kpi_summary`) |
| `notes` | string | Optional notes |

## Logic Rules

1. **RECOMMEND_HOLD** if Quality Gate fails or is missing.
2. **RECOMMEND_PUBLISH** if KPI baseline is missing (low confidence, "safe mode").
3. **RECOMMEND_PUBLISH** if Quality passed AND KPI trends are positive (High views/watch time).
4. **RECOMMEND_EDIT** if Quality passed BUT KPI trends are low (Suggests content improvement).

## Example

```json
{
  "schema_version": "v1",
  "generated_at": "2025-01-01T12:00:00Z",
  "run_id": "run-123",
  "decision": "recommend_publish",
  "confidence": 0.8,
  "reasons": ["KPI_UP"],
  "recommendations": [
    "Continue same topic cluster; consider sequel."
  ],
  "inputs_used": {
    "quality_gate": "output/run-123/artifacts/quality_gate_summary.json",
    "kpi_summary": "output/run-123/artifacts/kpi_summary.json"
  }
}
```
