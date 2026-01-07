import hashlib
import json
import logging
import os
import socket
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

from .model import NotifySummary, NotifyTarget, TargetResult
from .redact import redact_url

# Configure strict logging
logger = logging.getLogger(__name__)


def run(step: dict, run_dir: Path) -> str:
    """
    notify.webhook step entrypoint.
    Sends webhook notifications after decision.support.

    Args:
        step: Pipeline step configuration
        run_dir: Output directory for this run

    Returns:
        str: Path to the written artifact
    """
    # 1. Setup & Defaults
    run_id = run_dir.name
    start_time = datetime.utcnow()
    timestamp_utc = start_time.strftime("%Y-%m-%dT%H:%M:%SZ")

    notify_enabled = os.environ.get("NOTIFY_ENABLED", "false").lower() == "true"
    fail_open = os.environ.get("NOTIFY_FAIL_OPEN", "true").lower() == "true"
    timeout_seconds = int(os.environ.get("NOTIFY_TIMEOUT_SECONDS", "3"))

    # Initialize Summary State
    summary_status = "skipped"
    targets_attempted: list[TargetResult] = []
    reason_codes: list[str] = []
    message_digest = ""

    artifacts_dir = run_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    decision_path = artifacts_dir / "decision_support_summary.json"

    # 2. Pre-check: Status
    try:
        if not notify_enabled:
            reason_codes.append("WEBHOOK_DISABLED")

    except Exception as e:
        logger.error(f"Unexpected initialization error: {e}")
        if not fail_open:
            raise

    # 3. Load Inputs (Artifacts)
    if "WEBHOOK_DISABLED" in reason_codes:
        return _write_summary(
            run_id, timestamp_utc, "skipped", [], "", reason_codes, artifacts_dir
        )

    # Check config
    webhooks_json = os.environ.get("NOTIFY_WEBHOOKS_JSON", "")
    targets: list[NotifyTarget] = []

    if not webhooks_json:
        reason_codes.append("NO_TARGETS")
    else:
        try:
            raw_targets = json.loads(webhooks_json)
            if not isinstance(raw_targets, list):
                reason_codes.append("INVALID_CONFIG")
            else:
                seen_names = set()
                for t in raw_targets:
                    if len(targets) >= 10:
                        logger.warning("Max 10 targets reached, ignoring extras")
                        break

                    if not isinstance(t, dict) or "name" not in t or "url" not in t:
                        if "INVALID_CONFIG" not in reason_codes:
                            reason_codes.append("INVALID_CONFIG")
                        continue

                    name = t["name"]
                    url = t["url"]
                    if name in seen_names:
                        logger.warning(f"Duplicate target name '{name}', ignoring")
                        continue

                    seen_names.add(name)
                    targets.append(NotifyTarget(name=name, url=url))

                if not targets and "INVALID_CONFIG" not in reason_codes:
                    reason_codes.append("NO_TARGETS")

        except json.JSONDecodeError:
            reason_codes.append("INVALID_CONFIG")

    # If configuration issues, skip
    if reason_codes:
        _write_summary(
            run_id, timestamp_utc, "skipped", [], "", reason_codes, artifacts_dir
        )
        logger.warning(f"Notification skipped: {reason_codes}")
        if "INVALID_CONFIG" in reason_codes and not fail_open:
            raise ValueError("Invalid Notification Configuration")
        return str(artifacts_dir / "notify_summary.json")

    # 4. Message Generation
    if not decision_path.exists():
        reason_codes.append("MISSING_DECISION")
        return _write_summary(
            run_id, timestamp_utc, "skipped", [], "", reason_codes, artifacts_dir
        )

    try:
        with open(decision_path, encoding="utf-8") as f:
            decision_data = json.load(f)
    except Exception as e:
        logger.error(f"Failed to read decision summary: {e}")
        reason_codes.append("MISSING_DECISION")
        return _write_summary(
            run_id, timestamp_utc, "skipped", [], "", reason_codes, artifacts_dir
        )

    # Extract template fields
    decision = decision_data.get("decision", "unknown")
    try:
        confidence = f"{float(decision_data.get('formatted_confidence', 0.0)):.2f}"
    except (ValueError, TypeError):
        confidence = "0.00"

    reasons_list = decision_data.get("reasons", [])
    reasons_str = (
        ",".join(reasons_list) if isinstance(reasons_list, list) else str(reasons_list)
    )

    # Optional artifacts
    qgate_path = artifacts_dir / "quality_gate_summary.json"
    quality_gate = "missing"
    if qgate_path.exists():
        try:
            with open(qgate_path, encoding="utf-8") as f:
                qg_data = json.load(f)
                quality_gate = qg_data.get("status", "pass")
        except Exception:
            quality_gate = "error"

    # Built-in attributes map
    template_data = {
        "run_id": run_id,
        "decision": decision,
        "confidence": confidence,
        "quality_gate": quality_gate,
        "reasons": reasons_str,
        "artifacts_path": f"output/{run_id}/artifacts/",
    }

    # Render Template
    custom_template = os.environ.get("NOTIFY_MESSAGE_TEMPLATE")
    if custom_template:
        message_body = custom_template.format_map(SafeDict(template_data))
    else:
        message_body = (
            f"[dhamma-channel] decision={decision} confidence={confidence}\n"
            f"run_id: {run_id}\n"
            f"quality_gate: {quality_gate}\n"
            f"reasons: {reasons_str}\n"
            f"artifacts: output/{run_id}/artifacts/"
        )

    # Trim to 2000 chars
    if len(message_body) > 2000:
        message_body = message_body[:1997] + "..."

    # Compute Digest (excluding timestamp)
    message_digest = hashlib.sha256(message_body.encode("utf-8")).hexdigest()

    # 5. Send Webhooks (Generic POST)
    payload = json.dumps({"text": message_body}).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "DhammaChannelAutomation/1.0",
    }

    summary_status = "sent"

    for target in targets:
        redacted = redact_url(target.url)
        t_result = TargetResult(
            name=target.name, url_redacted=redacted, result="error", http_status=None
        )

        try:
            req = urllib.request.Request(
                target.url, data=payload, headers=headers, method="POST"
            )

            with urllib.request.urlopen(req, timeout=timeout_seconds) as response:
                t_result.http_status = response.status
                if 200 <= response.status < 300:
                    t_result.result = "success"
                else:
                    t_result.result = "error"
                    if "HTTP_ERROR" not in reason_codes:
                        reason_codes.append("HTTP_ERROR")

        except urllib.error.HTTPError as e:
            t_result.result = "error"
            t_result.http_status = e.code
            if "HTTP_ERROR" not in reason_codes:
                reason_codes.append("HTTP_ERROR")
            logger.warning(f"Webhook {target.name} failed: HTTP {e.code}")

        except urllib.error.URLError as e:
            if isinstance(e.reason, socket.timeout):
                t_result.result = "timeout"
                if "TIMEOUT" not in reason_codes:
                    reason_codes.append("TIMEOUT")
            else:
                t_result.result = "error"
                if "CONNECTION_ERROR" not in reason_codes:
                    reason_codes.append("CONNECTION_ERROR")
            logger.warning(f"Webhook {target.name} failed: {e.reason}")

        except Exception as e:
            t_result.result = "error"
            if "CONNECTION_ERROR" not in reason_codes:
                reason_codes.append("CONNECTION_ERROR")
            logger.warning(f"Webhook {target.name} unknown error: {e}")

        targets_attempted.append(t_result)

    success_count = sum(1 for t in targets_attempted if t.result == "success")
    if success_count == 0 and targets_attempted:
        summary_status = "failed"
    elif success_count > 0:
        summary_status = "sent"

    if summary_status == "sent":
        has_errors = any(t.result != "success" for t in targets_attempted)
        if not has_errors:
            reason_codes = []

    # 6. Write Summary
    path = _write_summary(
        run_id,
        timestamp_utc,
        summary_status,
        targets_attempted,
        message_digest,
        reason_codes,
        artifacts_dir,
    )

    # 7. Fail Open Check
    if summary_status == "failed" and not fail_open:
        raise RuntimeError(
            f"Notifications failed and fail_open is false. Reasons: {reason_codes}"
        )

    return path


def _write_summary(run_id, timestamp, status, targets, digest, reasons, artifacts_dir):
    summary = NotifySummary(
        run_id=run_id,
        timestamp_utc=timestamp,
        notification_status=status,
        targets_attempted=targets,
        message_digest=digest,
        reason_codes=reasons,
    )

    path = artifacts_dir / "notify_summary.json"
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(summary.json())
    except Exception:
        with open(path, "w", encoding="utf-8") as f:
            f.write(json.dumps(summary.dict(), indent=2))
    return str(path)


class SafeDict(dict):
    """Missing key safe formatter"""

    def __missing__(self, key):
        return "{" + key + "}"
