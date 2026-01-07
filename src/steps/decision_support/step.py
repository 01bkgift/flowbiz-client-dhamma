from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .model import DecisionEnum, DecisionSupportOutput

# KPI Thresholds
KPI_TOTAL_VIEWS_THRESHOLD = 1000
KPI_WATCH_TIME_THRESHOLD = 5000
KPI_SUBS_GAINED_THRESHOLD = 10


def _read_json_safe(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return None


def _get_missing_kpi_fallback(
    reasons: list[str], recommendations: list[str]
) -> tuple[DecisionEnum, float]:
    """Helper to populate reasons/recommendations for missing or incomplete KPI data."""
    decision = DecisionEnum.RECOMMEND_PUBLISH
    confidence = 0.60
    reasons.append("MISSING_KPI_BASELINE")

    # Avoid adding duplicate reasons if called multiple times (though logic flow prevents this usually)
    if "INCOMPLETE_KPI_DATA" not in reasons and "MISSING_KPI_BASELINE" not in reasons:
        pass  # Logic currently appends, caller handles specific reason codes additionally if needed

    recommendations.append(
        "Publish in the lowest-risk mode only (YouTube Community / safest adapter)."
    )
    recommendations.append(
        "Collect KPI baseline for 7–14 days, then enable KPI-based decisions."
    )
    return decision, confidence


def run_decision_support(step: dict[str, Any], run_dir: Path) -> Path:
    """
    Decision Support Step Implementation

    Generates a deterministic recommendation based on Quality Gate and KPI artifacts.
    """
    artifacts_dir = run_dir

    # Define input paths
    quality_gate_path = artifacts_dir / "quality_gate_summary.json"
    kpi_summary_path = artifacts_dir / "kpi_summary.json"

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
        decision, confidence = _get_missing_kpi_fallback(reasons, recommendations)

    # R4: Quality Pass + KPI Present
    else:
        # Compute simple KPI trend
        total_views = kpi_data.get("total_views")
        watch_time = kpi_data.get("total_watch_time_minutes")
        subs_gained = kpi_data.get("total_subscribers_gained")

        # Check presence
        if total_views is None or watch_time is None or subs_gained is None:
            # Treat as missing KPI baseline (R3 fallback)
            decision, confidence = _get_missing_kpi_fallback(reasons, recommendations)
            if "INCOMPLETE_KPI_DATA" not in reasons:
                reasons.append("INCOMPLETE_KPI_DATA")
        else:
            # Thresholds
            kpi_up = (
                (total_views >= KPI_TOTAL_VIEWS_THRESHOLD)
                or (watch_time >= KPI_WATCH_TIME_THRESHOLD)
                or (subs_gained >= KPI_SUBS_GAINED_THRESHOLD)
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
    final_run_id = step.get("run_id")
    if not final_run_id:
        # Fallback to inferring run_id from the run directory path.
        try:
            if run_dir.name == "artifacts":
                final_run_id = run_dir.parent.name
            else:
                final_run_id = run_dir.name
        except Exception:
            final_run_id = "unknown_run_id"

    if not final_run_id:
        final_run_id = "unknown_run_id"

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
