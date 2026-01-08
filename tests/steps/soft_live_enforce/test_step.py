import os
import sys
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.automation_core.youtube_upload import upload_video
from src.steps.soft_live_enforce.step import (
    SOFT_LIVE_ENABLED_VAR,
    SOFT_LIVE_FAIL_CLOSED_VAR,
    SOFT_LIVE_YOUTUBE_MODE_VAR,
    run_soft_live_enforce,
)


@contextmanager
def env_vars(vars_dict):
    original = dict(os.environ)
    os.environ.update(vars_dict)
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(original)


@pytest.fixture
def tmp_run_dir(tmp_path):
    run_id = "test_run_123"
    (tmp_path / "output" / run_id / "artifacts").mkdir(parents=True)
    return tmp_path, run_id


def test_soft_live_disabled(tmp_run_dir):
    base_dir, run_id = tmp_run_dir
    with env_vars({SOFT_LIVE_ENABLED_VAR: "false"}):
        summary, _ = run_soft_live_enforce(run_id, base_dir=base_dir)
        assert summary["soft_live_status"] == "disabled"
        assert summary["enforced_mode"] is None


def test_soft_live_enabled_valid_mode(tmp_run_dir):
    base_dir, run_id = tmp_run_dir
    with env_vars({
        SOFT_LIVE_ENABLED_VAR: "true",
        SOFT_LIVE_YOUTUBE_MODE_VAR: "unlisted"
    }):
        summary, _ = run_soft_live_enforce(run_id, base_dir=base_dir)
        assert summary["soft_live_status"] == "enabled"
        assert summary["enforced_mode"] == "unlisted"
        assert summary["reason_codes"] == []


def test_soft_live_enabled_invalid_mode_fail_closed(tmp_run_dir):
    base_dir, run_id = tmp_run_dir
    with env_vars({
        SOFT_LIVE_ENABLED_VAR: "true",
        SOFT_LIVE_YOUTUBE_MODE_VAR: "invalid_mode",
        SOFT_LIVE_FAIL_CLOSED_VAR: "true"
    }):
        with pytest.raises(ValueError, match="Invalid SOFT_LIVE_YOUTUBE_MODE"):
            run_soft_live_enforce(run_id, base_dir=base_dir)


def test_soft_live_enabled_invalid_mode_fail_open(tmp_run_dir):
    base_dir, run_id = tmp_run_dir
    with env_vars({
        SOFT_LIVE_ENABLED_VAR: "true",
        SOFT_LIVE_YOUTUBE_MODE_VAR: "invalid_mode",
        SOFT_LIVE_FAIL_CLOSED_VAR: "false"
    }):
        summary, _ = run_soft_live_enforce(run_id, base_dir=base_dir)
        assert summary["soft_live_status"] == "enabled"
        assert summary["enforced_mode"] == "dry_run"
        assert "INVALID_CONFIG" in summary["reason_codes"]
        assert "FALLBACK_DRY_RUN" in summary["reason_codes"]


def test_upload_video_enforces_dry_run():
    # Test that upload_video returns dummy ID when Soft-Live dry_run is on
    with env_vars({
        SOFT_LIVE_ENABLED_VAR: "true",
        SOFT_LIVE_YOUTUBE_MODE_VAR: "dry_run"
    }):
        with patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.is_file", return_value=True):
            vid = upload_video(
                mp4_path=Path("dummy.mp4"),
                title="test",
                description="desc",
                tags=[],
                privacy_status="public"
            )
            assert vid == "soft-live-dry-run-video-id"


def test_upload_video_overrides_public_to_unlisted():
    with env_vars({
        SOFT_LIVE_ENABLED_VAR: "true",
        SOFT_LIVE_YOUTUBE_MODE_VAR: "unlisted"
    }):
        # Mock the google apis part since we expect it to TRY to proceed to upload,
        # but with modified privacy status.
        # However, since deps might be missing or auth missing, checks might fail later.
        # But we can verify the logging or logic by mocking the part AFTER enforcement.

        # In the modified code, it checks env vars first.
        # Then imports.
        # We want to verify `privacy_status` changed locally variable.
        # Since we can't inspect local variables of a function easily,
        # let's mock the `googleapiclient.http.MediaFileUpload` and `youtube.videos().insert`

        with patch("src.automation_core.youtube_upload._require_env") as mock_env:
            mock_env.return_value = "dummy"

            with patch.dict("sys.modules", {
                "google.auth.exceptions": MagicMock(),
                "google.auth.transport.requests": MagicMock(),
                "google.oauth2.credentials": MagicMock(),
                "googleapiclient.discovery": MagicMock(),
                "googleapiclient.errors": MagicMock(),
                "googleapiclient.http": MagicMock(),
            }):
                # Need to reload or force import if modules were already imported?
                # The function modifies imports inside try-except.
                # Assuming dependencies are mocked correctly.

                # Mock build()
                mock_build = MagicMock()
                mock_youtube = MagicMock()
                mock_build.return_value = mock_youtube

                sys.modules["googleapiclient.discovery"].build = mock_build

                # Mock inserts
                mock_videos = MagicMock()
                mock_insert = MagicMock()
                mock_youtube.videos.return_value = mock_videos
                mock_videos.insert.return_value = mock_insert
                mock_insert.execute.return_value = {"id": "real_upload_id"}

                # Mock Path checks
                with patch("pathlib.Path.exists", return_value=True), \
                     patch("pathlib.Path.is_file", return_value=True):

                    upload_video(
                        mp4_path=Path("video.mp4"),
                        title="test",
                        description="desc",
                        tags=[],
                        privacy_status="public" # Request PUBLIC
                    )

                    # Verify insert called with unlisted
                    args, kwargs = mock_videos.insert.call_args
                    body = kwargs.get("body", {})
                    assert body["status"]["privacyStatus"] == "unlisted"

def test_upload_video_allows_private_when_unlisted_enforced():
    with env_vars({
        SOFT_LIVE_ENABLED_VAR: "true",
        SOFT_LIVE_YOUTUBE_MODE_VAR: "unlisted"
    }):
        with patch("src.automation_core.youtube_upload._require_env") as mock_env:
            mock_env.return_value = "dummy"
            with patch.dict("sys.modules", {
                "google.auth.exceptions": MagicMock(),
                "google.oauth2.credentials": MagicMock(),
                "googleapiclient.discovery": MagicMock(),
                "googleapiclient.errors": MagicMock(),
                "googleapiclient.http": MagicMock(),
            }):
                mock_videos = MagicMock()
                sys.modules["googleapiclient.discovery"].build.return_value.videos.return_value = mock_videos
                mock_videos.insert.return_value.execute.return_value = {"id": "id"}

                with patch("pathlib.Path.exists", return_value=True), \
                     patch("pathlib.Path.is_file", return_value=True):

                    upload_video(
                        mp4_path=Path("video.mp4"),
                        title="test",
                        description="desc",
                        tags=[],
                        privacy_status="private" # Request PRIVATE (stricter than unlisted)
                    )

                    # Should remain private
                    args, kwargs = mock_videos.insert.call_args
                    body = kwargs.get("body", {})
                    assert body["status"]["privacyStatus"] == "private"

def test_upload_video_disabled_soft_live_respects_input():
    with env_vars({SOFT_LIVE_ENABLED_VAR: "false"}):
         with patch("src.automation_core.youtube_upload._require_env") as mock_env:
            mock_env.return_value = "dummy"
            with patch.dict("sys.modules", {
                "google.auth.exceptions": MagicMock(),
                "google.oauth2.credentials": MagicMock(),
                "googleapiclient.discovery": MagicMock(),
                "googleapiclient.errors": MagicMock(),
                "googleapiclient.http": MagicMock(),
            }):
                mock_videos = MagicMock()
                sys.modules["googleapiclient.discovery"].build.return_value.videos.return_value = mock_videos
                mock_videos.insert.return_value.execute.return_value = {"id": "id"}

                with patch("pathlib.Path.exists", return_value=True), \
                     patch("pathlib.Path.is_file", return_value=True):

                    upload_video(
                        mp4_path=Path("video.mp4"),
                        title="test",
                        description="desc",
                        tags=[],
                        privacy_status="public"
                    )

                    # Should remain public
                    args, kwargs = mock_videos.insert.call_args
                    body = kwargs.get("body", {})
                    assert body["status"]["privacyStatus"] == "public"
