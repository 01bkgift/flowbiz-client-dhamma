import json
import os
from datetime import datetime
from unittest import mock
from urllib.error import HTTPError, URLError

import pytest

# Import the step module
from src.steps.notify_webhook import step as notify_step


@pytest.fixture
def mock_run_dir(tmp_path):
    run_dir = tmp_path / "output" / "run_test_123"
    run_dir.mkdir(parents=True)
    (run_dir / "artifacts").mkdir()
    return run_dir


@pytest.fixture
def mock_decision_artifact(mock_run_dir):
    data = {
        "decision": "recommend_publish",
        "formatted_confidence": 0.95,
        "reasons": ["high_score", "safe_content"],
    }
    with open(mock_run_dir / "artifacts" / "decision_support_summary.json", "w") as f:
        json.dump(data, f)
    return data


@pytest.fixture
def basic_env():
    env = {
        "NOTIFY_ENABLED": "true",
        "NOTIFY_WEBHOOKS_JSON": '[{"name": "test_hook", "url": "https://discord.com/api/webhooks/1234/token"}]',
        "NOTIFY_TIMEOUT_SECONDS": "1",
        "NOTIFY_FAIL_OPEN": "true",
    }
    with mock.patch.dict(os.environ, env, clear=True):
        yield env


def get_summary(run_dir):
    path = run_dir / "artifacts" / "notify_summary.json"
    with open(path) as f:
        return json.load(f)


def test_disabled_by_default(mock_run_dir):
    # NOTIFY_ENABLED default should be false if not set
    # We clear environ to test default
    with mock.patch.dict(os.environ, {}, clear=True):
        notify_step.run({}, mock_run_dir)

    summary = get_summary(mock_run_dir)
    assert summary["notification_status"] == "skipped"
    assert "WEBHOOK_DISABLED" in summary["reason_codes"]


def test_disabled_explicitly(mock_run_dir):
    with mock.patch.dict(os.environ, {"NOTIFY_ENABLED": "false"}, clear=True):
        notify_step.run({}, mock_run_dir)

    summary = get_summary(mock_run_dir)
    assert summary["notification_status"] == "skipped"
    assert "WEBHOOK_DISABLED" in summary["reason_codes"]


def test_no_targets(mock_run_dir):
    with mock.patch.dict(
        os.environ, {"NOTIFY_ENABLED": "true", "NOTIFY_WEBHOOKS_JSON": "[]"}, clear=True
    ):
        notify_step.run({}, mock_run_dir)

    summary = get_summary(mock_run_dir)
    assert summary["notification_status"] == "skipped"
    assert "NO_TARGETS" in summary["reason_codes"]


def test_missing_decision_artifact(mock_run_dir, basic_env):
    # Ensure no artifact exists
    pass
    # (mock_run_dir setup creates dir but not file unless mock_decision_artifact fixture used)

    notify_step.run({}, mock_run_dir)
    summary = get_summary(mock_run_dir)
    assert summary["notification_status"] == "skipped"
    assert "MISSING_DECISION" in summary["reason_codes"]


def test_success_send(mock_run_dir, basic_env, mock_decision_artifact):
    with mock.patch("urllib.request.urlopen") as mock_urlopen:
        # Mock successful response
        mock_response = mock.Mock()
        mock_response.status = 204
        mock_response.__enter__ = mock.Mock(return_value=mock_response)
        mock_response.__exit__ = mock.Mock(return_value=None)
        mock_urlopen.return_value = mock_response

        notify_step.run({}, mock_run_dir)

        summary = get_summary(mock_run_dir)
        assert summary["notification_status"] == "sent"
        assert len(summary["targets_attempted"]) == 1
        assert summary["targets_attempted"][0]["result"] == "success"
        assert summary["targets_attempted"][0]["http_status"] == 204
        assert summary["reason_codes"] == []

        # Check request payload
        args, _ = mock_urlopen.call_args
        req = args[0]
        assert req.full_url == "https://discord.com/api/webhooks/1234/token"
        assert b"recommend_publish" in req.data
        assert req.headers["Content-type"] == "application/json"


def test_redaction_in_summary(mock_run_dir, basic_env, mock_decision_artifact):
    with mock.patch("urllib.request.urlopen") as mock_urlopen:
        mock_response = mock.Mock()
        mock_response.status = 200
        mock_response.__enter__ = mock.Mock(return_value=mock_response)
        mock_response.__exit__ = mock.Mock(return_value=None)
        mock_urlopen.return_value = mock_response

        notify_step.run({}, mock_run_dir)

        summary = get_summary(mock_run_dir)
        target = summary["targets_attempted"][0]
        assert "1234/token" not in target["url_redacted"]
        assert target["url_redacted"].endswith("***oken") or target[
            "url_redacted"
        ].endswith("***oken")  # 'token' last 4 is 'oken'
        assert "discord.com" in target["url_redacted"]


def test_http_error_fail_open(mock_run_dir, basic_env, mock_decision_artifact):
    with mock.patch("urllib.request.urlopen") as mock_urlopen:
        # Simulate HTTP Error
        mock_urlopen.side_effect = HTTPError("url", 500, "Server Error", {}, None)

        # Should NOT raise exception because Fail Open is True
        notify_step.run({}, mock_run_dir)

        summary = get_summary(mock_run_dir)
        assert summary["notification_status"] == "failed"
        assert "HTTP_ERROR" in summary["reason_codes"]
        assert summary["targets_attempted"][0]["result"] == "error"
        assert summary["targets_attempted"][0]["http_status"] == 500


def test_timeout_fail_open(mock_run_dir, basic_env, mock_decision_artifact):
    with mock.patch("urllib.request.urlopen") as mock_urlopen:
        # Simulate Timeout
        mock_urlopen.side_effect = URLError(TimeoutError())

        notify_step.run({}, mock_run_dir)

        summary = get_summary(mock_run_dir)
        assert summary["notification_status"] == "failed"
        assert "TIMEOUT" in summary["reason_codes"]
        assert summary["targets_attempted"][0]["result"] == "timeout"


def test_determinism_message_digest(mock_run_dir, basic_env, mock_decision_artifact):
    # Two runs with different times should have SAME message digest (if content identical)

    with mock.patch("urllib.request.urlopen") as mock_urlopen:
        mock_response = mock.Mock()
        mock_response.status = 200
        mock_response.__enter__ = mock.Mock(return_value=mock_response)
        mock_response.__exit__ = mock.Mock(return_value=None)
        mock_urlopen.return_value = mock_response

        # Run 1
        with mock.patch("src.steps.notify_webhook.step.datetime") as mock_dt:
            mock_dt.utcnow.return_value = datetime(2024, 1, 1, 12, 0, 0)
            notify_step.run({}, mock_run_dir)
        summary1 = get_summary(mock_run_dir)

        # Run 2 (different time)
        with mock.patch("src.steps.notify_webhook.step.datetime") as mock_dt:
            mock_dt.utcnow.return_value = datetime(2024, 1, 2, 12, 0, 0)
            notify_step.run({}, mock_run_dir)
        summary2 = get_summary(mock_run_dir)

        assert summary1["message_digest"] == summary2["message_digest"]
        assert summary1["timestamp_utc"] != summary2["timestamp_utc"]


def test_malformed_config(mock_run_dir):
    with mock.patch.dict(
        os.environ,
        {"NOTIFY_ENABLED": "true", "NOTIFY_WEBHOOKS_JSON": "{not: json}"},
        clear=True,
    ):
        notify_step.run({}, mock_run_dir)

    summary = get_summary(mock_run_dir)
    assert summary["notification_status"] == "skipped"
    assert "INVALID_CONFIG" in summary["reason_codes"]


def test_duplicate_target_names(mock_run_dir, mock_decision_artifact):
    # duplicate names, verify only first used and logged
    targets = [
        {"name": "hook1", "url": "http://a.com"},
        {"name": "hook1", "url": "http://b.com"},  # Duplicate
        {"name": "hook2", "url": "http://c.com"},
    ]
    with mock.patch.dict(
        os.environ,
        {"NOTIFY_ENABLED": "true", "NOTIFY_WEBHOOKS_JSON": json.dumps(targets)},
        clear=True,
    ):
        with mock.patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = mock.Mock()
            mock_response.status = 200
            mock_response.__enter__ = mock.Mock(return_value=mock_response)
            mock_response.__exit__ = mock.Mock(return_value=None)
            mock_urlopen.return_value = mock_response

            notify_step.run({}, mock_run_dir)

    summary = get_summary(mock_run_dir)
    assert len(summary["targets_attempted"]) == 2
    names = [t["name"] for t in summary["targets_attempted"]]
    assert names == ["hook1", "hook2"]
    # Check that hook1 url corresponds to first one (redacted check difficult without deep mock check)
    # But count proves dedup.


def test_max_targets(mock_run_dir, mock_decision_artifact):
    targets = [{"name": f"hook{i}", "url": f"http://site.com/{i}"} for i in range(15)]
    with mock.patch.dict(
        os.environ,
        {"NOTIFY_ENABLED": "true", "NOTIFY_WEBHOOKS_JSON": json.dumps(targets)},
        clear=True,
    ):
        with mock.patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = mock.Mock()
            mock_response.status = 200
            mock_response.__enter__ = mock.Mock(return_value=mock_response)
            mock_response.__exit__ = mock.Mock(return_value=None)
            mock_urlopen.return_value = mock_response

            notify_step.run({}, mock_run_dir)

    summary = get_summary(mock_run_dir)
    assert len(summary["targets_attempted"]) == 10
    assert summary["targets_attempted"][-1]["name"] == "hook9"
