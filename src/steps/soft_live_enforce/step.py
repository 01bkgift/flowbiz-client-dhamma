import os
from datetime import UTC, datetime
from pathlib import Path

from .model import SoftLiveSummary

SOFT_LIVE_ENABLED_VAR = "SOFT_LIVE_ENABLED"
SOFT_LIVE_YOUTUBE_MODE_VAR = "SOFT_LIVE_YOUTUBE_MODE"
SOFT_LIVE_FAIL_CLOSED_VAR = "SOFT_LIVE_FAIL_CLOSED"
DEFAULT_YOUTUBE_MODE = "dry_run"


def run_soft_live_enforce(run_id: str, base_dir: Path | None = None) -> tuple[dict, Path]:
    """
    Enforces Soft-Live mode by checking environment variables and generating a summary artifact.

    Args:
        run_id: The pipeline run ID
        base_dir: The base directory of the project (default to current directory)

    Returns:
        tuple containing the summary dictionary and the path to the written artifact
    """
    if base_dir is None:
        base_dir = Path.cwd()

    output_dir = base_dir / "output" / run_id / "artifacts"
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "soft_live_summary.json"

    env_enabled = os.environ.get(SOFT_LIVE_ENABLED_VAR, "true").strip().lower() == "true"
    env_mode = os.environ.get(SOFT_LIVE_YOUTUBE_MODE_VAR, DEFAULT_YOUTUBE_MODE).strip().lower()
    env_fail_closed = os.environ.get(SOFT_LIVE_FAIL_CLOSED_VAR, "true").strip().lower() == "true"

    timestamp_utc = datetime.now(UTC).isoformat().replace("+00:00", "Z")

    if not env_enabled:
        # Disabled
        summary = SoftLiveSummary(
            run_id=run_id,
            timestamp_utc=timestamp_utc,
            soft_live_status="disabled",
            enforced_mode=None,
            reason_codes=[],
        )
        _write_summary(summary_path, summary)
        return summary.model_dump(), summary_path

    # Enabled validation
    valid_modes = {"dry_run", "unlisted", "private"}
    enforced_mode = env_mode if env_mode in valid_modes else None

    if enforced_mode:
        summary = SoftLiveSummary(
            run_id=run_id,
            timestamp_utc=timestamp_utc,
            soft_live_status="enabled",
            enforced_mode=enforced_mode,
            reason_codes=[],
        )
        _write_summary(summary_path, summary)
        return summary.model_dump(), summary_path

    # Invalid mode handling
    if env_fail_closed:
        raise ValueError(
            f"Invalid SOFT_LIVE_YOUTUBE_MODE: '{env_mode}'. Allowed: {valid_modes}"
        )
    else:
        # Fallback to dry_run
        summary = SoftLiveSummary(
            run_id=run_id,
            timestamp_utc=timestamp_utc,
            soft_live_status="enabled",
            enforced_mode="dry_run",
            reason_codes=["INVALID_CONFIG", "FALLBACK_DRY_RUN"],
        )
        _write_summary(summary_path, summary)
        return summary.model_dump(), summary_path


def _write_summary(path: Path, summary: SoftLiveSummary):
    with open(path, "w", encoding="utf-8") as f:
        f.write(summary.model_dump_json(indent=2))
