# Soft-Live Summary Contract (v1)

## Overview

This artifact is produced by the `soft_live.enforce` step to certify the execution mode of the pipeline regarding public visibility. It acts as an audit record for "Soft-Live" protections.

## Location

`output/<run_id>/artifacts/soft_live_summary.json`

## Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": [
    "schema_version",
    "run_id",
    "timestamp_utc",
    "soft_live_status",
    "enforced_mode",
    "reason_codes"
  ],
  "properties": {
    "schema_version": {
      "type": "string",
      "const": "v1"
    },
    "run_id": {
      "type": "string",
      "description": "Unique identifier for the current pipeline run."
    },
    "timestamp_utc": {
      "type": "string",
      "format": "date-time",
      "description": "ISO8601 UTC timestamp of enforcement check (Z suffix)."
    },
    "soft_live_status": {
      "type": "string",
      "enum": ["enabled", "disabled", "failed"],
      "description": "Overall status of the soft-live protection."
    },
    "enforced_mode": {
      "type": ["string", "null"],
      "enum": ["dry_run", "unlisted", "private", null],
      "description": "The enforced visibility mode if enabled. Null if disabled or failed."
    },
    "reason_codes": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "description": "List of strings explaining overrides, fallbacks, or errors. Empty on normal success."
    }
  }
}
```

## Reason Codes (Common)

- `INVALID_CONFIG`: The provided configuration was invalid.
- `FALLBACK_DRY_RUN`: The system fell back to dry_run due to invalid config (fail-open behavior).
- `OVERRIDE_APPLIED`: (In logs/other contexts) Indicates soft-live forced a change.
