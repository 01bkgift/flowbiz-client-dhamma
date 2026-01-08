import json
import os
import sys
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.automation_core.youtube_upload import (
    _extract_content_fingerprint,
    _generate_deterministic_fake_id,
    _normalize_title,
    upload_video,
)
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
    with env_vars(
        {SOFT_LIVE_ENABLED_VAR: "true", SOFT_LIVE_YOUTUBE_MODE_VAR: "unlisted"}
    ):
        summary, _ = run_soft_live_enforce(run_id, base_dir=base_dir)
        assert summary["soft_live_status"] == "enabled"
        assert summary["enforced_mode"] == "unlisted"
        assert summary["reason_codes"] == []


def test_soft_live_enabled_invalid_mode_fail_closed(tmp_run_dir):
    base_dir, run_id = tmp_run_dir
    with env_vars(
        {
            SOFT_LIVE_ENABLED_VAR: "true",
            SOFT_LIVE_YOUTUBE_MODE_VAR: "invalid_mode",
            SOFT_LIVE_FAIL_CLOSED_VAR: "true",
        }
    ):
        with pytest.raises(ValueError, match="Invalid SOFT_LIVE_YOUTUBE_MODE"):
            run_soft_live_enforce(run_id, base_dir=base_dir)


def test_soft_live_enabled_invalid_mode_fail_open(tmp_run_dir):
    base_dir, run_id = tmp_run_dir
    with env_vars(
        {
            SOFT_LIVE_ENABLED_VAR: "true",
            SOFT_LIVE_YOUTUBE_MODE_VAR: "invalid_mode",
            SOFT_LIVE_FAIL_CLOSED_VAR: "false",
        }
    ):
        summary, _ = run_soft_live_enforce(run_id, base_dir=base_dir)
        assert summary["soft_live_status"] == "enabled"
        assert summary["enforced_mode"] == "dry_run"
        assert "INVALID_CONFIG" in summary["reason_codes"]
        assert "FALLBACK_DRY_RUN" in summary["reason_codes"]


@pytest.fixture
def mock_google_apis():
    with patch("src.automation_core.youtube_upload._require_env") as mock_env:
        mock_env.return_value = "dummy"
        with patch.dict(
            "sys.modules",
            {
                "google.auth.exceptions": MagicMock(),
                "google.auth.transport.requests": MagicMock(),
                "google.oauth2.credentials": MagicMock(),
                "googleapiclient.discovery": MagicMock(),
                "googleapiclient.errors": MagicMock(),
                "googleapiclient.http": MagicMock(),
            },
        ):
            mock_build = MagicMock()
            mock_youtube = MagicMock()
            mock_build.return_value = mock_youtube
            sys.modules["googleapiclient.discovery"].build = mock_build

            mock_videos = MagicMock()
            mock_insert = MagicMock()
            mock_youtube.videos.return_value = mock_videos
            mock_videos.insert.return_value = mock_insert
            mock_insert.execute.return_value = {"id": "real_upload_id"}

            yield mock_videos


# =======================
# NEW TESTS: Content Fingerprinting & Normalization
# =======================


def test_normalization():
    """Test title normalization (Unicode, whitespace, case)."""
    assert _normalize_title("  Test   Title  ") == "test title"
    assert _normalize_title("TeSt") == "test"
    assert _normalize_title("Test\u2000Title") == "test title"  # Unicode space
    # NFKC normalization example
    assert _normalize_title("ﬁle") == "file"  # fi ligature -> fi


def test_fake_id_with_fingerprint(tmp_path):
    """Test that fake ID changes when content changes (collision prevention)."""
    run_dir = tmp_path / "output" / "run1"
    artifacts_dir = run_dir / "artifacts"
    artifacts_dir.mkdir(parents=True)

    # Create metadata.json with content A
    metadata_a = {"title": "Video Title", "description": "Description A"}
    (artifacts_dir / "metadata.json").write_text(json.dumps(metadata_a))

    id_a = _generate_deterministic_fake_id("Video Title", "dry_run", run_dir)

    # Change content (same title, different description)
    metadata_b = {"title": "Video Title", "description": "Description B"}
    (artifacts_dir / "metadata.json").write_text(json.dumps(metadata_b))

    id_b = _generate_deterministic_fake_id("Video Title", "dry_run", run_dir)

    # IDs should be different (collision prevented)
    assert id_a != id_b
    assert id_a.startswith("soft-live-dry-")
    assert id_b.startswith("soft-live-dry-")


def test_fake_id_same_content_same_id(tmp_path):
    """Test idempotency: same content -> same ID."""
    run_dir = tmp_path / "output" / "run1"
    artifacts_dir = run_dir / "artifacts"
    artifacts_dir.mkdir(parents=True)

    metadata = {"title": "Video Title", "description": "Same Description"}
    (artifacts_dir / "metadata.json").write_text(json.dumps(metadata))

    id1 = _generate_deterministic_fake_id("Video Title", "dry_run", run_dir)
    id2 = _generate_deterministic_fake_id("Video Title", "dry_run", run_dir)

    assert id1 == id2


def test_fake_id_artifact_priority(tmp_path):
    """Test fingerprint extraction priority: video_render_summary > metadata > script."""
    run_dir = tmp_path / "output" / "run1"
    artifacts_dir = run_dir / "artifacts"
    artifacts_dir.mkdir(parents=True)

    # Create all three artifacts
    (artifacts_dir / "video_render_summary.json").write_text(
        json.dumps({"text_sha256_12": "abc123456789"})
    )
    (artifacts_dir / "metadata.json").write_text(
        json.dumps({"title": "Title", "description": "Desc"})
    )
    (artifacts_dir / "script.json").write_text(json.dumps({"content": "script"}))

    # Should use video_render_summary (priority 1)
    fingerprint = _extract_content_fingerprint(run_dir)
    assert fingerprint == "abc123456789"

    # Remove video_render_summary, should fall back to metadata
    (artifacts_dir / "video_render_summary.json").unlink()
    fingerprint = _extract_content_fingerprint(run_dir)
    assert fingerprint is not None
    assert len(fingerprint) == 12  # SHA256[:12]


def test_fake_id_missing_artifacts_legacy_fallback(tmp_path):
    """Test legacy behavior when no artifacts present."""
    run_dir = tmp_path / "output" / "run1"
    # Don't create artifacts dir

    id1 = _generate_deterministic_fake_id("Title", "dry_run", run_dir)
    id2 = _generate_deterministic_fake_id("Title", "dry_run", run_dir)

    # Should still be deterministic (title + mode only)
    assert id1 == id2
    assert id1.startswith("soft-live-dry-")


def test_fake_id_normalization_matters(tmp_path):
    """Test that normalization makes different titles produce same ID."""
    run_dir = tmp_path / "output" / "run1"
    artifacts_dir = run_dir / "artifacts"
    artifacts_dir.mkdir(parents=True)

    (artifacts_dir / "metadata.json").write_text(
        json.dumps({"title": "Test", "description": "Desc"})
    )

    id1 = _generate_deterministic_fake_id("  Test  ", "dry_run", run_dir)
    id2 = _generate_deterministic_fake_id("TEST", "dry_run", run_dir)
    id3 = _generate_deterministic_fake_id("test", "dry_run", run_dir)

    # All should produce same ID due to normalization
    assert id1 == id2 == id3


# =======================
# EXISTING TESTS (unchanged)
# =======================


def test_upload_video_enforces_dry_run_deterministic():
    # Test that upload_video returns deterministic ID based on title+mode
    with env_vars(
        {SOFT_LIVE_ENABLED_VAR: "true", SOFT_LIVE_YOUTUBE_MODE_VAR: "dry_run"}
    ):
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.is_file", return_value=True),
        ):
            # Run 1
            vid1 = upload_video(
                mp4_path=Path("dummy.mp4"),
                title="test_title_A",
                description="desc",
                tags=[],
                privacy_status="public",
            )

            # Run 2 (Same title)
            vid2 = upload_video(
                mp4_path=Path("dummy.mp4"),
                title="test_title_A",
                description="desc",
                tags=[],
                privacy_status="public",
            )

            # Run 3 (Different title)
            vid3 = upload_video(
                mp4_path=Path("dummy.mp4"),
                title="test_title_B",
                description="desc",
                tags=[],
                privacy_status="public",
            )

            assert vid1 == vid2
            assert vid1 != vid3
            assert vid1.startswith("soft-live-dry-")


def test_soft_live_rejects_public_mode_fail_closed():
    # Test STRICT safety: public is NOT allowed in Soft-Live mode config
    # fail_closed=true (default env assumption if not set,
    # but here we test the enforcement inside video_upload which might return fallback ID)
    # Actually, current impl returns FALLBACK ID.
    # Let's verify it returns default FALLBACK ID and prints violation.

    with env_vars(
        {
            SOFT_LIVE_ENABLED_VAR: "true",
            SOFT_LIVE_YOUTUBE_MODE_VAR: "public",  # ILLEGAL CONFIG
        }
    ):
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.is_file", return_value=True),
        ):
            vid = upload_video(
                mp4_path=Path("dummy.mp4"),
                title="test",
                description="desc",
                tags=[],
                privacy_status="public",
            )

            assert vid == "soft-live-fallback-dry-run-id"


def test_upload_video_overrides_public_to_unlisted(mock_google_apis):
    with env_vars(
        {SOFT_LIVE_ENABLED_VAR: "true", SOFT_LIVE_YOUTUBE_MODE_VAR: "unlisted"}
    ):
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.is_file", return_value=True),
        ):
            upload_video(
                mp4_path=Path("video.mp4"),
                title="test",
                description="desc",
                tags=[],
                privacy_status="public",  # Request PUBLIC
            )

            # Verify insert called with unlisted
            args, kwargs = mock_google_apis.insert.call_args
            body = kwargs.get("body", {})
            assert body["status"]["privacyStatus"] == "unlisted"


def test_upload_video_allows_private_when_unlisted_enforced(mock_google_apis):
    with env_vars(
        {SOFT_LIVE_ENABLED_VAR: "true", SOFT_LIVE_YOUTUBE_MODE_VAR: "unlisted"}
    ):
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.is_file", return_value=True),
        ):
            upload_video(
                mp4_path=Path("video.mp4"),
                title="test",
                description="desc",
                tags=[],
                privacy_status="private",  # Request PRIVATE (stricter than unlisted)
            )

            # Should remain private
            args, kwargs = mock_google_apis.insert.call_args
            body = kwargs.get("body", {})
            assert body["status"]["privacyStatus"] == "private"


def test_upload_video_disabled_soft_live_respects_input(mock_google_apis):
    with env_vars({SOFT_LIVE_ENABLED_VAR: "false"}):
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.is_file", return_value=True),
        ):
            upload_video(
                mp4_path=Path("video.mp4"),
                title="test",
                description="desc",
                tags=[],
                privacy_status="public",
            )

            # Should remain public
            args, kwargs = mock_google_apis.insert.call_args
            body = kwargs.get("body", {})
            assert body["status"]["privacyStatus"] == "public"
