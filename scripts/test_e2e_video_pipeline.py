#!/usr/bin/env python3
"""
Test script for End-to-End Video Production Pipeline.
Flow: TTS -> Video Render -> Quality Gate -> Approval Gate -> Soft Live -> YouTube Upload (dry_run)

Usage:
    python scripts/test_e2e_video_pipeline.py [--run-id RUN_ID] [--dry-run]
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Setup paths
ROOT_DIR = Path(__file__).parent.parent.resolve()
ORCHESTRATOR_PATH = ROOT_DIR / "orchestrator.py"
PIPELINE_PATH = ROOT_DIR / "pipelines" / "e2e_video_youtube_test.yaml"


def log(msg, level="INFO"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] [{level}] {msg}")


def assert_file_exists(path: Path, description: str):
    if not path.exists():
        log(f"FAIL: {description} not found at {path}", "ERROR")
        return False
    # Check if empty (some steps might create empty files on failure)
    if path.stat().st_size == 0:
        log(f"FAIL: {description} is empty at {path}", "ERROR")
        return False
    log(f"PASS: {description} exists", "INFO")
    return True


def assert_json_field(path: Path, field: str, expected_value, description: str):
    if not path.exists():
        log(f"SKIP: Cannot check {description}, file not found", "WARN")
        return False

    try:
        data = json.loads(path.read_text("utf-8"))

        # Handle dot notation for nested fields vs simple field access
        if "." in field:
            keys = field.split(".")
            current = data
            for k in keys:
                if isinstance(current, dict):
                    current = current.get(k)
                else:
                    current = None
                    break
            actual_value = current
        else:
            actual_value = data.get(field)

        if actual_value != expected_value:
            log(
                f"FAIL: {description} (Field '{field}'): Expected '{expected_value}', Got '{actual_value}'",
                "ERROR",
            )
            return False

        log(f"PASS: {description} (Field '{field}' == '{expected_value}')", "INFO")
        return True
    except (json.JSONDecodeError, OSError) as e:
        log(f"FAIL: Error reading or parsing {description}: {e}", "ERROR")
        return False


def check_video_properties(video_path: Path):
    """Verify video resolution and duration using ffprobe."""
    try:
        # Use existing imports (subprocess, json, Path, log)
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height,duration",
            "-of",
            "json",
            str(video_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)

        width = data["streams"][0]["width"]
        height = data["streams"][0]["height"]
        duration = float(data["streams"][0].get("duration", 0))

        log(
            f"Video Properties: Resolution={width}x{height}, Duration={duration:.2f}s",
            "INFO",
        )

        if width != 1920 or height != 1080:
            log(
                f"FAIL: Resolution mismatch. Expected 1920x1080, got {width}x{height}",
                "ERROR",
            )
            return False

        if duration <= 0:
            log("FAIL: Invalid video duration", "ERROR")
            return False

        return True
    except Exception as e:
        log(f"FAIL: Could not verify video properties: {e}", "ERROR")
        return False


def run_test(run_id: str, dry_run: bool = False):
    log(f"Starting E2E Video Pipeline Test with Run ID: {run_id}")

    # Add local ffmpeg to PATH if it exists
    local_ffmpeg = ROOT_DIR / "external" / "ffmpeg"
    if local_ffmpeg.exists():
        os.environ["PATH"] = str(local_ffmpeg) + os.pathsep + os.environ.get("PATH", "")
        log(f"Added local ffmpeg to PATH: {local_ffmpeg}")

    # Setup Environment for orchestrator
    env = os.environ.copy()

    env["SOFT_LIVE_ENABLED"] = "true"
    env["SOFT_LIVE_YOUTUBE_MODE"] = "dry_run"
    env["SOFT_LIVE_FAIL_CLOSED"] = "true"
    env["APPROVAL_ENABLED"] = "false"  # Instant approval
    env["PIPELINE_DRY_RUN"] = "true" if dry_run else "false"

    # Inject Pipeline Params for post_templates validation
    env["PIPELINE_PARAMS_JSON"] = json.dumps(
        {
            "platform": "youtube",
            "title": "E2E Test Video",
            "lang": "th",
            "description": "E2E Test Video Description",
        }
    )

    # Pre-create metadata.json to allow post_templates to find 'platform'
    # This is a fallback/robustness measure if env var injection fails
    output_dir = ROOT_DIR / "output" / run_id
    output_dir.mkdir(parents=True, exist_ok=True)
    metadata_path = output_dir / "metadata.json"
    metadata_content = {
        "title": "E2E Test Video",
        "description": "Auto-generated E2E test video",
        "platform": "youtube",
        "language": "th",
    }
    metadata_path.write_text(json.dumps(metadata_content, indent=2), encoding="utf-8")
    log(f"Pre-created metadata.json at {metadata_path}")

    # Ensure assets and fixtures exist
    fixture_path = ROOT_DIR / "scripts" / "test_fixtures" / "e2e_voiceover_script.txt"
    if not fixture_path.exists():
        log("FAIL: Test fixture not found. Create it first.", "ERROR")
        return False

    # 2. Run Orchestrator
    cmd = [
        sys.executable,
        str(ORCHESTRATOR_PATH),
        "--pipeline",
        str(PIPELINE_PATH),
        "--run-id",
        run_id,
    ]

    log(f"Executing: {' '.join(cmd)}")
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)

    # Check execution result
    if result.returncode != 0:
        log("FAIL: Orchestrator failed", "ERROR")
        print("--- STDERR ---")
        print(result.stderr)
        print("--- STDOUT ---")
        print(result.stdout)
        return False

    log("PASS: Orchestrator executed successfully", "INFO")

    # 3. Verify Artifacts
    artifacts_dir = ROOT_DIR / "output" / run_id / "artifacts"
    log(f"Verifying artifacts in: {artifacts_dir}")

    all_passed = True

    # A. Voiceover Summary
    all_passed &= assert_file_exists(
        artifacts_dir / "voiceover_summary.json", "Voiceover Summary"
    )

    # B. Video Render Summary
    all_passed &= assert_file_exists(
        artifacts_dir / "video_render_summary.json", "Video Render Summary"
    )

    # C. Output MP4 Existence (Check path from summary if possible, or fallback to known pattern)
    # Ideally verify path contract
    video_summary_path = artifacts_dir / "video_render_summary.json"
    if video_summary_path.exists():
        try:
            video_data = json.loads(video_summary_path.read_text("utf-8"))
            mp4_rel_path = video_data.get("output_mp4_path")
            if mp4_rel_path:
                output_mp4_full_path = ROOT_DIR / mp4_rel_path
                mp4_file_exists = assert_file_exists(
                    output_mp4_full_path, "Output MP4 File"
                )
                all_passed &= mp4_file_exists
                # After checking file existence, check properties
                if mp4_file_exists:
                    all_passed &= check_video_properties(output_mp4_full_path)
            else:
                log(
                    "FAIL: output_mp4_path missing in video_render_summary.json",
                    "ERROR",
                )
                all_passed = False
        except Exception as e:
            log(f"FAIL: Could not check output MP4 path: {e}", "ERROR")
            all_passed = False

    # D. Quality Gate
    all_passed &= assert_file_exists(
        artifacts_dir / "quality_gate_summary.json", "Quality Gate Summary"
    )
    all_passed &= assert_json_field(
        artifacts_dir / "quality_gate_summary.json",
        "decision",
        "pass",
        "Quality Gate Decision",
    )

    # E. Decision Support
    all_passed &= assert_file_exists(
        artifacts_dir / "decision_support_summary.json", "Decision Support Summary"
    )

    # F. Approval Gate (Should be approved automatically due to grace_period=0)
    all_passed &= assert_file_exists(
        artifacts_dir / "approval_gate_summary.json", "Approval Gate Summary"
    )
    all_passed &= assert_json_field(
        artifacts_dir / "approval_gate_summary.json",
        "status",
        "approved_by_timeout",
        "Approval Status",
    )

    # G. Soft Live
    all_passed &= assert_file_exists(
        artifacts_dir / "soft_live_summary.json", "Soft Live Summary"
    )
    all_passed &= assert_json_field(
        artifacts_dir / "soft_live_summary.json",
        "enforced_mode",
        "dry_run",
        "Soft Live Enforced Mode",
    )

    # H. YouTube Upload
    # The test pipeline is configured with dry_run: true in the youtube.upload step.
    # This should result in a summary file indicating a successful dry-run.
    all_passed &= assert_file_exists(
        artifacts_dir / "youtube_upload_summary.json", "YouTube Upload Summary"
    )

    if all_passed:
        log("SUCCESS: All E2E verification checks passed!", "INFO")
        return True
    else:
        log("FAIL: One or more E2E verification checks failed.", "ERROR")
        return False


def main():
    parser = argparse.ArgumentParser(description="Run E2E Video Pipeline Test")
    parser.add_argument(
        "--run-id",
        help="Custom run ID",
        default=f"e2e_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run orchestrator in dry-run mode (no actual generation)",
    )

    args = parser.parse_args()

    success = run_test(args.run_id, args.dry_run)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
