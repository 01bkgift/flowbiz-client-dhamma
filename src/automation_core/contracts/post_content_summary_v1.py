from __future__ import annotations

from typing import Any

from automation_core.contracts.common import _artifact_rel_path, _validate_run_id

POST_SUMMARY_NAME = "post_content_summary.json"


def _post_summary_rel_path(run_id: str, *, validate: bool = True) -> str:
    if validate:
        run_id = _validate_run_id(run_id)
    return _artifact_rel_path(run_id, POST_SUMMARY_NAME, validate=False)


def validate_post_content_summary(data: dict[str, Any], run_id: str) -> dict[str, Any]:
    """Validate post_content_summary payload (v1)."""
    if not isinstance(data, dict):
        raise ValueError("post_content_summary must be an object")
    if data.get("schema_version") != "v1":
        raise ValueError("post_content_summary.schema_version must be 'v1'")
    if data.get("engine") != "post_templates":
        raise ValueError("post_content_summary.engine must be 'post_templates'")
    summary_run_id = data.get("run_id")
    if summary_run_id is None or summary_run_id != run_id:
        raise ValueError("post_content_summary.run_id must match run_id")

    inputs = data.get("inputs")
    if not isinstance(inputs, dict):
        raise ValueError("post_content_summary.inputs must be an object")
    platform = inputs.get("platform")
    if not isinstance(platform, str) or not platform.strip():
        raise ValueError("post_content_summary.inputs.platform is required")

    outputs = data.get("outputs")
    if not isinstance(outputs, dict):
        raise ValueError("post_content_summary.outputs must be an object")
    for key in ("short", "long"):
        value = outputs.get(key)
        if not isinstance(value, str):
            raise ValueError(f"post_content_summary.outputs.{key} must be a string")
    return data
