from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .model import DecisionEnum, DecisionSupportOutput


def _read_json_safe(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return None


def run_decision_support(step: dict[str, Any], run_dir: Path) -> Path:
    """
    Decision Support Step Implementation

    Generates a deterministic recommendation based on Quality Gate and KPI artifacts.
    """
    # Resolve paths (run_dir is expected to be output/<run_id>/artifacts/..)
    # Actually, based on orchestrator.py, run_dir might be output/<run_id>/ or output/<run_id>/artifacts/
    # Let's assume standard layout. If run_dir has "artifacts" in it, use it.
    # Otherwise, check if "artifacts" subdir exists.

    # In orchestrator.py: out = run_dir / step["output"]
    # Usually step["output"] is just filename.
    # So run_dir seems to be the directory where artifacts should be written.

    artifacts_dir = run_dir

    # Define input paths
    quality_gate_path = artifacts_dir / "quality_gate_summary.json"
    kpi_summary_path = artifacts_dir / "kpi_summary.json"
    # Fallback for KPI if missing in current run (from PR11)
    # The prompt says: output/<run_id>/artifacts/kpi_summary.json OR the KPI artifact produced by PR11
    # We will look for kpi_summary.json in the artifacts dir.

    # Read inputs
    quality_data = _read_json_safe(quality_gate_path)
    kpi_data = _read_json_safe(kpi_summary_path)

    inputs_used = {}
    if quality_data:
        inputs_used["quality_gate"] = str(quality_gate_path)
    if kpi_data:
        inputs_used["kpi_summary"] = str(kpi_summary_path)

    # Initialize decision variables
    decision: DecisionEnum
    confidence: float
    reasons: list[str] = []
    recommendations: list[str] = []

    # Logic Implementation

    # R1: Quality Fail
    if quality_data and quality_data.get("decision") == "fail":
        decision = DecisionEnum.RECOMMEND_HOLD
        confidence = 0.95
        reasons.append("QUALITY_FAIL")
        recommendations.append("Fix issues from quality gate, re-run pipeline.")

    # R2: Quality Missing
    elif not quality_data:
        decision = DecisionEnum.RECOMMEND_HOLD
        confidence = 0.70
        reasons.append("MISSING_QUALITY_GATE")
        recommendations.append(
            "Run quality gate to produce deterministic pass/fail before publish."
        )

    # R3: KPI Missing
    elif not kpi_data:
        decision = DecisionEnum.RECOMMEND_PUBLISH
        confidence = 0.60
        reasons.append("MISSING_KPI_BASELINE")
        recommendations.append(
            "Publish in the lowest-risk mode only (YouTube Community / safest adapter)."
        )
        recommendations.append(
            "Collect KPI baseline for 7–14 days, then enable KPI-based decisions."
        )

    # R4: Quality Pass + KPI Present
    else:
        # Compute simple KPI trend
        # read total_views, total_watch_time_minutes, total_subscribers_gained
        total_views = kpi_data.get("total_views")
        watch_time = kpi_data.get("total_watch_time_minutes")
        subs_gained = kpi_data.get("total_subscribers_gained")

        # Check presence
        if total_views is None or watch_time is None or subs_gained is None:
            # Treat as missing KPI baseline (R3 fallback)
            decision = DecisionEnum.RECOMMEND_PUBLISH
            confidence = 0.60
            reasons.append("MISSING_KPI_BASELINE")
            reasons.append("INCOMPLETE_KPI_DATA")
            recommendations.append(
                "Publish in the lowest-risk mode only (YouTube Community / safest adapter)."
            )
            recommendations.append(
                "Collect KPI baseline for 7–14 days, then enable KPI-based decisions."
            )
        else:
            # Thresholds
            kpi_up = (
                (total_views >= 1000) or (watch_time >= 5000) or (subs_gained >= 10)
            )

            if kpi_up:
                decision = DecisionEnum.RECOMMEND_PUBLISH
                confidence = 0.80
                reasons.append("KPI_UP")
                recommendations.append("Continue same topic cluster; consider sequel.")
            else:
                decision = DecisionEnum.RECOMMEND_EDIT
                confidence = 0.75
                reasons.append("KPI_LOW")
                recommendations.append("Review video hook (first 10s).")
                recommendations.append("Optimize title and thumbnail for CTR.")
                recommendations.append("Add stronger Call to Action (CTA).")
                recommendations.append("Consider re-editing opening sequence.")

    # Construct Output
    run_id = step.get("run_id", "unknown_run_id")
    # run_id might not be in step dict, but is required for schema.
    # orchestrator often passes run_id separately?
    # In orchestrator logic I saw earlier: run_id parameter in functions.
    # But here the signature I guessed is `(step, run_dir)`.
    # I will extract run_id from run_dir path if possible or optional.
    # The output schema requires run_id.

    # Try to extract from run_dir path (output/<run_id>/artifacts)
    try:
        # if run_dir is .../output/run-123/artifacts
        if run_dir.name == "artifacts":
            inferred_run_id = run_dir.parent.name
        else:
            inferred_run_id = run_dir.name
    except Exception:
        inferred_run_id = "unknown"

    # Use run_id if available somehow, else inferred
    final_run_id = inferred_run_id

    output_model = DecisionSupportOutput(
        generated_at=datetime.now(UTC).isoformat(),
        run_id=final_run_id,
        decision=decision,
        confidence=confidence,
        reasons=reasons,
        recommendations=recommendations,
        inputs_used=inputs_used,
        notes="Automated decision support generated by decision.support step.",
    )

    # Write output
    output_filename = step.get("output", "decision_support_summary.json")
    output_path = artifacts_dir / output_filename

    # Ensure dir exists (should already)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_path.write_text(output_model.model_dump_json(indent=2), encoding="utf-8")

    return output_path
