"""
ทดสอบโมดูล youtube_upload สำหรับการอัปโหลดวิดีโอขึ้น YouTube

ไฟล์นี้ทดสอบฟีเจอร์ต่างๆ ของระบบอัปโหลด YouTube ได้แก่:
- การตรวจสอบความถูกต้องของ input parameters
- การจัดการข้อผิดพลาดเมื่อขาดตัวแปรสภาพแวดล้อม
- พฤติกรรมของ custom exception classes
- edge cases เช่น การกรองแท็กที่ไม่ใช่ string
"""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from automation_core.youtube_upload import (
    YoutubeApiError,
    YoutubeAuthMissingError,
    YoutubeDepsMissingError,
    YoutubeUploadError,
    _require_env,
    upload_video,
)


@pytest.fixture
def mock_google_api():
    """Fixture สำหรับ mock Google API modules ที่ถูก lazy-import"""
    # Create mock modules
    mock_google = Mock()
    mock_google_auth = Mock()
    mock_google_auth_exceptions = Mock()
    mock_google_auth_transport = Mock()
    mock_google_auth_transport_requests = Mock()
    mock_google_oauth2 = Mock()
    mock_google_oauth2_credentials = Mock()
    mock_googleapiclient = Mock()
    mock_googleapiclient_discovery = Mock()
    mock_googleapiclient_errors = Mock()
    mock_googleapiclient_http = Mock()

    # Create mock classes
    mock_credentials_class = Mock()
    mock_credentials_instance = Mock()
    mock_credentials_class.return_value = mock_credentials_instance

    mock_request_class = Mock()
    mock_build_func = Mock()
    mock_media_upload_class = Mock()

    # Create proper mock exception classes
    class MockHttpError(Exception):
        """Mock HttpError with resp attribute"""

        def __init__(self, message):
            super().__init__(message)
            self.resp = None

    class MockRefreshError(Exception):
        """Mock RefreshError exception"""

        pass

    mock_http_error_class = MockHttpError
    mock_refresh_error_class = MockRefreshError

    # Setup module attributes
    mock_google_auth_exceptions.RefreshError = mock_refresh_error_class
    mock_google_auth_transport_requests.Request = mock_request_class
    mock_google_oauth2_credentials.Credentials = mock_credentials_class
    mock_googleapiclient_discovery.build = mock_build_func
    mock_googleapiclient_errors.HttpError = mock_http_error_class
    mock_googleapiclient_http.MediaFileUpload = mock_media_upload_class

    modules = {
        "google": mock_google,
        "google.auth": mock_google_auth,
        "google.auth.exceptions": mock_google_auth_exceptions,
        "google.auth.transport": mock_google_auth_transport,
        "google.auth.transport.requests": mock_google_auth_transport_requests,
        "google.oauth2": mock_google_oauth2,
        "google.oauth2.credentials": mock_google_oauth2_credentials,
        "googleapiclient": mock_googleapiclient,
        "googleapiclient.discovery": mock_googleapiclient_discovery,
        "googleapiclient.errors": mock_googleapiclient_errors,
        "googleapiclient.http": mock_googleapiclient_http,
    }

    with patch.dict("sys.modules", modules):
        yield {
            "Credentials": mock_credentials_class,
            "credentials_instance": mock_credentials_instance,
            "Request": mock_request_class,
            "build": mock_build_func,
            "MediaFileUpload": mock_media_upload_class,
            "HttpError": mock_http_error_class,
            "RefreshError": mock_refresh_error_class,
        }


class TestRequireEnv:
    """ทดสอบฟังก์ชัน _require_env สำหรับการอ่านตัวแปรสภาพแวดล้อม"""

    def test_require_env_with_valid_value(self, monkeypatch):
        """ทดสอบว่า _require_env คืนค่าที่ถูกต้องเมื่อตัวแปรมีค่า"""
        monkeypatch.setenv("TEST_VAR", "test_value")
        result = _require_env("TEST_VAR")
        assert result == "test_value"

    def test_require_env_trims_whitespace(self, monkeypatch):
        """ทดสอบว่า _require_env ตัด whitespace ข้างหน้าและข้างหลัง"""
        monkeypatch.setenv("TEST_VAR", "  test_value  ")
        result = _require_env("TEST_VAR")
        assert result == "test_value"

    def test_require_env_raises_when_missing(self, monkeypatch):
        """ทดสอบว่า _require_env raise YoutubeAuthMissingError เมื่อไม่มีตัวแปร"""
        monkeypatch.delenv("TEST_VAR", raising=False)
        with pytest.raises(YoutubeAuthMissingError) as exc_info:
            _require_env("TEST_VAR")
        assert "TEST_VAR" in str(exc_info.value)
        assert "Missing required YouTube auth environment variable" in str(
            exc_info.value
        )

    def test_require_env_raises_when_empty_string(self, monkeypatch):
        """ทดสอบว่า _require_env raise YoutubeAuthMissingError เมื่อค่าเป็นสตริงว่าง"""
        monkeypatch.setenv("TEST_VAR", "")
        with pytest.raises(YoutubeAuthMissingError) as exc_info:
            _require_env("TEST_VAR")
        assert "TEST_VAR" in str(exc_info.value)

    def test_require_env_raises_when_only_whitespace(self, monkeypatch):
        """ทดสอบว่า _require_env raise YoutubeAuthMissingError เมื่อค่ามีแต่ whitespace"""
        monkeypatch.setenv("TEST_VAR", "   \t\n  ")
        with pytest.raises(YoutubeAuthMissingError) as exc_info:
            _require_env("TEST_VAR")
        assert "TEST_VAR" in str(exc_info.value)


class TestCustomExceptions:
    """ทดสอบ custom exception classes"""

    def test_youtube_upload_error_is_exception(self):
        """ทดสอบว่า YoutubeUploadError สืบทอดจาก Exception"""
        exc = YoutubeUploadError("test message")
        assert isinstance(exc, Exception)
        assert str(exc) == "test message"

    def test_youtube_deps_missing_error_is_youtube_upload_error(self):
        """ทดสอบว่า YoutubeDepsMissingError สืบทอดจาก YoutubeUploadError"""
        exc = YoutubeDepsMissingError("deps missing")
        assert isinstance(exc, YoutubeUploadError)
        assert isinstance(exc, Exception)
        assert str(exc) == "deps missing"

    def test_youtube_auth_missing_error_is_youtube_upload_error(self):
        """ทดสอบว่า YoutubeAuthMissingError สืบทอดจาก YoutubeUploadError"""
        exc = YoutubeAuthMissingError("auth missing")
        assert isinstance(exc, YoutubeUploadError)
        assert isinstance(exc, Exception)
        assert str(exc) == "auth missing"

    def test_youtube_api_error_is_youtube_upload_error(self):
        """ทดสอบว่า YoutubeApiError สืบทอดจาก YoutubeUploadError"""
        exc = YoutubeApiError("api error")
        assert isinstance(exc, YoutubeUploadError)
        assert isinstance(exc, Exception)
        assert str(exc) == "api error"

    def test_youtube_api_error_with_status(self):
        """ทดสอบว่า YoutubeApiError สามารถเก็บ status code ได้"""
        exc = YoutubeApiError("api error", status=403)
        assert exc.status == 403
        assert str(exc) == "api error"

    def test_youtube_api_error_without_status(self):
        """ทดสอบว่า YoutubeApiError มี status เป็น None ได้"""
        exc = YoutubeApiError("api error")
        assert exc.status is None
        assert str(exc) == "api error"


class TestUploadVideoInputValidation:
    """ทดสอบการตรวจสอบความถูกต้องของ input parameters"""

    def test_upload_video_raises_when_file_not_exists(self, tmp_path):
        """ทดสอบว่า upload_video raise YoutubeUploadError เมื่อไฟล์ไม่พบ"""
        non_existent = tmp_path / "does_not_exist.mp4"
        with pytest.raises(YoutubeUploadError) as exc_info:
            upload_video(
                non_existent,
                "Test Title",
                "Test Description",
                ["tag1"],
                "public",
            )
        assert "does not exist" in str(exc_info.value).lower()
        assert str(non_existent) in str(exc_info.value)

    def test_upload_video_raises_when_path_is_directory(self, tmp_path):
        """ทดสอบว่า upload_video raise YoutubeUploadError เมื่อ path เป็นไดเรกทอรี"""
        directory = tmp_path / "test_dir"
        directory.mkdir()
        with pytest.raises(YoutubeUploadError) as exc_info:
            upload_video(
                directory,
                "Test Title",
                "Test Description",
                ["tag1"],
                "public",
            )
        assert "not a file" in str(exc_info.value).lower()

    def test_upload_video_converts_str_to_path(
        self, tmp_path, monkeypatch, mock_google_api
    ):
        """ทดสอบว่า upload_video สามารถรับ string path และแปลงเป็น Path ได้"""
        # Create a mock video file
        video_file = tmp_path / "test.mp4"
        video_file.write_bytes(b"fake video content")

        # Setup environment variables
        monkeypatch.setenv("YOUTUBE_CLIENT_ID", "test_id")
        monkeypatch.setenv("YOUTUBE_CLIENT_SECRET", "test_secret")
        monkeypatch.setenv("YOUTUBE_REFRESH_TOKEN", "test_token")

        # Setup mocks
        mock_youtube = Mock()
        mock_request = Mock()
        mock_request.execute.return_value = {"id": "test_video_id"}
        mock_youtube.videos().insert.return_value = mock_request
        mock_google_api["build"].return_value = mock_youtube

        # Call with string path
        result = upload_video(
            str(video_file),  # Pass as string, not Path
            "Test Title",
            "Test Description",
            ["tag1"],
            "public",
        )
        assert result == "test_video_id"

    def test_upload_video_raises_when_title_empty(self, tmp_path):
        """ทดสอบว่า upload_video raise YoutubeUploadError เมื่อ title เป็นสตริงว่าง"""
        video_file = tmp_path / "test.mp4"
        video_file.write_bytes(b"fake video")

        with pytest.raises(YoutubeUploadError) as exc_info:
            upload_video(
                video_file,
                "",
                "Test Description",
                ["tag1"],
                "public",
            )
        assert "title" in str(exc_info.value).lower()
        assert "non-empty" in str(exc_info.value).lower()

    def test_upload_video_raises_when_title_only_whitespace(self, tmp_path):
        """ทดสอบว่า upload_video raise YoutubeUploadError เมื่อ title มีแต่ whitespace"""
        video_file = tmp_path / "test.mp4"
        video_file.write_bytes(b"fake video")

        with pytest.raises(YoutubeUploadError) as exc_info:
            upload_video(
                video_file,
                "   \t\n  ",
                "Test Description",
                ["tag1"],
                "public",
            )
        assert "title" in str(exc_info.value).lower()

    def test_upload_video_raises_when_title_not_string(self, tmp_path):
        """ทดสอบว่า upload_video raise YoutubeUploadError เมื่อ title ไม่ใช่ string"""
        video_file = tmp_path / "test.mp4"
        video_file.write_bytes(b"fake video")

        with pytest.raises(YoutubeUploadError) as exc_info:
            upload_video(
                video_file,
                123,  # type: ignore
                "Test Description",
                ["tag1"],
                "public",
            )
        assert "title" in str(exc_info.value).lower()

    def test_upload_video_raises_when_description_empty(self, tmp_path):
        """ทดสอบว่า upload_video raise YoutubeUploadError เมื่อ description เป็นสตริงว่าง"""
        video_file = tmp_path / "test.mp4"
        video_file.write_bytes(b"fake video")

        with pytest.raises(YoutubeUploadError) as exc_info:
            upload_video(
                video_file,
                "Test Title",
                "",
                ["tag1"],
                "public",
            )
        assert "description" in str(exc_info.value).lower()
        assert "non-empty" in str(exc_info.value).lower()

    def test_upload_video_raises_when_description_only_whitespace(self, tmp_path):
        """ทดสอบว่า upload_video raise YoutubeUploadError เมื่อ description มีแต่ whitespace"""
        video_file = tmp_path / "test.mp4"
        video_file.write_bytes(b"fake video")

        with pytest.raises(YoutubeUploadError) as exc_info:
            upload_video(
                video_file,
                "Test Title",
                "   \t\n  ",
                ["tag1"],
                "public",
            )
        assert "description" in str(exc_info.value).lower()

    def test_upload_video_raises_when_description_not_string(self, tmp_path):
        """ทดสอบว่า upload_video raise YoutubeUploadError เมื่อ description ไม่ใช่ string"""
        video_file = tmp_path / "test.mp4"
        video_file.write_bytes(b"fake video")

        with pytest.raises(YoutubeUploadError) as exc_info:
            upload_video(
                video_file,
                "Test Title",
                None,  # type: ignore
                ["tag1"],
                "public",
            )
        assert "description" in str(exc_info.value).lower()

    def test_upload_video_raises_when_privacy_status_invalid(self, tmp_path):
        """ทดสอบว่า upload_video raise YoutubeUploadError เมื่อ privacy_status ไม่ถูกต้อง"""
        video_file = tmp_path / "test.mp4"
        video_file.write_bytes(b"fake video")

        with pytest.raises(YoutubeUploadError) as exc_info:
            upload_video(
                video_file,
                "Test Title",
                "Test Description",
                ["tag1"],
                "invalid_status",
            )
        assert "privacy_status" in str(exc_info.value).lower()
        assert "private" in str(exc_info.value)
        assert "public" in str(exc_info.value)
        assert "unlisted" in str(exc_info.value)

    def test_upload_video_raises_when_privacy_status_not_string(self, tmp_path):
        """ทดสอบว่า upload_video raise YoutubeUploadError เมื่อ privacy_status ไม่ใช่ string"""
        video_file = tmp_path / "test.mp4"
        video_file.write_bytes(b"fake video")

        with pytest.raises(YoutubeUploadError) as exc_info:
            upload_video(
                video_file,
                "Test Title",
                "Test Description",
                ["tag1"],
                None,  # type: ignore
            )
        assert "privacy_status" in str(exc_info.value).lower()

    def test_upload_video_accepts_all_valid_privacy_statuses(
        self, tmp_path, monkeypatch, mock_google_api
    ):
        """ทดสอบว่า upload_video ยอมรับ privacy_status ที่ถูกต้องทั้งหมด"""
        video_file = tmp_path / "test.mp4"
        video_file.write_bytes(b"fake video")

        # Setup environment and mocks
        monkeypatch.setenv("YOUTUBE_CLIENT_ID", "test_id")
        monkeypatch.setenv("YOUTUBE_CLIENT_SECRET", "test_secret")
        monkeypatch.setenv("YOUTUBE_REFRESH_TOKEN", "test_token")

        valid_statuses = ["private", "unlisted", "public"]

        for status in valid_statuses:
            # Setup mocks for each iteration
            mock_youtube = Mock()
            mock_request = Mock()
            mock_request.execute.return_value = {"id": f"video_{status}"}
            mock_youtube.videos().insert.return_value = mock_request
            mock_google_api["build"].return_value = mock_youtube

            result = upload_video(
                video_file,
                "Test Title",
                "Test Description",
                ["tag1"],
                status,
            )
            assert result == f"video_{status}"


class TestUploadVideoTagsFiltering:
    """ทดสอบการกรองแท็กที่ไม่ใช่ string"""

    def test_upload_video_filters_non_string_tags(
        self, tmp_path, monkeypatch, mock_google_api
    ):
        """ทดสอบว่า upload_video กรองแท็กที่ไม่ใช่ string ออก"""
        video_file = tmp_path / "test.mp4"
        video_file.write_bytes(b"fake video")

        monkeypatch.setenv("YOUTUBE_CLIENT_ID", "test_id")
        monkeypatch.setenv("YOUTUBE_CLIENT_SECRET", "test_secret")
        monkeypatch.setenv("YOUTUBE_REFRESH_TOKEN", "test_token")

        mock_youtube = Mock()
        mock_request = Mock()
        mock_request.execute.return_value = {"id": "test_video_id"}
        mock_youtube.videos().insert.return_value = mock_request
        mock_google_api["build"].return_value = mock_youtube

        # Mix of string and non-string tags
        mixed_tags = ["tag1", 123, "tag2", None, "tag3", {"key": "value"}]
        upload_video(
            video_file,
            "Test Title",
            "Test Description",
            mixed_tags,  # type: ignore
            "public",
        )

        # Verify only string tags were passed to the API
        call_args = mock_youtube.videos().insert.call_args
        body = call_args.kwargs["body"]
        assert body["snippet"]["tags"] == ["tag1", "tag2", "tag3"]

    def test_upload_video_handles_empty_tags_list(
        self, tmp_path, monkeypatch, mock_google_api
    ):
        """ทดสอบว่า upload_video จัดการ tags ว่างได้ถูกต้อง"""
        video_file = tmp_path / "test.mp4"
        video_file.write_bytes(b"fake video")

        monkeypatch.setenv("YOUTUBE_CLIENT_ID", "test_id")
        monkeypatch.setenv("YOUTUBE_CLIENT_SECRET", "test_secret")
        monkeypatch.setenv("YOUTUBE_REFRESH_TOKEN", "test_token")

        mock_youtube = Mock()
        mock_request = Mock()
        mock_request.execute.return_value = {"id": "test_video_id"}
        mock_youtube.videos().insert.return_value = mock_request
        mock_google_api["build"].return_value = mock_youtube

        upload_video(
            video_file,
            "Test Title",
            "Test Description",
            [],
            "public",
        )

        call_args = mock_youtube.videos().insert.call_args
        body = call_args.kwargs["body"]
        assert body["snippet"]["tags"] == []

    def test_upload_video_handles_none_tags(
        self, tmp_path, monkeypatch, mock_google_api
    ):
        """ทดสอบว่า upload_video จัดการ tags เป็น None ได้"""
        video_file = tmp_path / "test.mp4"
        video_file.write_bytes(b"fake video")

        monkeypatch.setenv("YOUTUBE_CLIENT_ID", "test_id")
        monkeypatch.setenv("YOUTUBE_CLIENT_SECRET", "test_secret")
        monkeypatch.setenv("YOUTUBE_REFRESH_TOKEN", "test_token")

        mock_youtube = Mock()
        mock_request = Mock()
        mock_request.execute.return_value = {"id": "test_video_id"}
        mock_youtube.videos().insert.return_value = mock_request
        mock_google_api["build"].return_value = mock_youtube

        upload_video(
            video_file,
            "Test Title",
            "Test Description",
            None,  # type: ignore
            "public",
        )

        call_args = mock_youtube.videos().insert.call_args
        body = call_args.kwargs["body"]
        assert body["snippet"]["tags"] == []


class TestUploadVideoAuthErrors:
    """ทดสอบการจัดการข้อผิดพลาดเกี่ยวกับการยืนยันตัวตน"""

    def test_upload_video_raises_when_missing_client_id(
        self, tmp_path, monkeypatch, mock_google_api
    ):
        """ทดสอบว่า upload_video raise YoutubeAuthMissingError เมื่อขาด YOUTUBE_CLIENT_ID"""
        video_file = tmp_path / "test.mp4"
        video_file.write_bytes(b"fake video")

        monkeypatch.delenv("YOUTUBE_CLIENT_ID", raising=False)
        monkeypatch.setenv("YOUTUBE_CLIENT_SECRET", "test_secret")
        monkeypatch.setenv("YOUTUBE_REFRESH_TOKEN", "test_token")

        with pytest.raises(YoutubeAuthMissingError) as exc_info:
            upload_video(
                video_file,
                "Test Title",
                "Test Description",
                ["tag1"],
                "public",
            )
        assert "YOUTUBE_CLIENT_ID" in str(exc_info.value)

    def test_upload_video_raises_when_missing_client_secret(
        self, tmp_path, monkeypatch, mock_google_api
    ):
        """ทดสอบว่า upload_video raise YoutubeAuthMissingError เมื่อขาด YOUTUBE_CLIENT_SECRET"""
        video_file = tmp_path / "test.mp4"
        video_file.write_bytes(b"fake video")

        monkeypatch.setenv("YOUTUBE_CLIENT_ID", "test_id")
        monkeypatch.delenv("YOUTUBE_CLIENT_SECRET", raising=False)
        monkeypatch.setenv("YOUTUBE_REFRESH_TOKEN", "test_token")

        with pytest.raises(YoutubeAuthMissingError) as exc_info:
            upload_video(
                video_file,
                "Test Title",
                "Test Description",
                ["tag1"],
                "public",
            )
        assert "YOUTUBE_CLIENT_SECRET" in str(exc_info.value)

    def test_upload_video_raises_when_missing_refresh_token(
        self, tmp_path, monkeypatch, mock_google_api
    ):
        """ทดสอบว่า upload_video raise YoutubeAuthMissingError เมื่อขาด YOUTUBE_REFRESH_TOKEN"""
        video_file = tmp_path / "test.mp4"
        video_file.write_bytes(b"fake video")

        monkeypatch.setenv("YOUTUBE_CLIENT_ID", "test_id")
        monkeypatch.setenv("YOUTUBE_CLIENT_SECRET", "test_secret")
        monkeypatch.delenv("YOUTUBE_REFRESH_TOKEN", raising=False)

        with pytest.raises(YoutubeAuthMissingError) as exc_info:
            upload_video(
                video_file,
                "Test Title",
                "Test Description",
                ["tag1"],
                "public",
            )
        assert "YOUTUBE_REFRESH_TOKEN" in str(exc_info.value)


class TestUploadVideoDepsMissing:
    """ทดสอบการจัดการข้อผิดพลาดเมื่อขาด Google API dependencies"""

    def test_upload_video_raises_when_google_deps_missing(self, tmp_path, monkeypatch):
        """ทดสอบว่า upload_video raise YoutubeDepsMissingError เมื่อขาด Google API libs"""
        video_file = tmp_path / "test.mp4"
        video_file.write_bytes(b"fake video")

        monkeypatch.setenv("YOUTUBE_CLIENT_ID", "test_id")
        monkeypatch.setenv("YOUTUBE_CLIENT_SECRET", "test_secret")
        monkeypatch.setenv("YOUTUBE_REFRESH_TOKEN", "test_token")

        # Use a more targeted approach to simulate missing imports
        import builtins

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name.startswith("google"):
                raise ImportError(f"No module named '{name}'")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)

        with pytest.raises(YoutubeDepsMissingError) as exc_info:
            upload_video(
                video_file,
                "Test Title",
                "Test Description",
                ["tag1"],
                "public",
            )
        assert "dependencies" in str(exc_info.value).lower()


class TestUploadVideoApiErrors:
    """ทดสอบการจัดการข้อผิดพลาดจาก YouTube API"""

    def test_upload_video_raises_when_auth_refresh_fails(
        self, tmp_path, monkeypatch, mock_google_api
    ):
        """ทดสอบว่า upload_video raise YoutubeApiError เมื่อ refresh token ล้มเหลว"""
        video_file = tmp_path / "test.mp4"
        video_file.write_bytes(b"fake video")

        monkeypatch.setenv("YOUTUBE_CLIENT_ID", "test_id")
        monkeypatch.setenv("YOUTUBE_CLIENT_SECRET", "test_secret")
        monkeypatch.setenv("YOUTUBE_REFRESH_TOKEN", "test_token")

        # Make refresh raise RefreshError
        mock_google_api["credentials_instance"].refresh.side_effect = mock_google_api[
            "RefreshError"
        ]("Refresh failed")

        with pytest.raises(YoutubeApiError) as exc_info:
            upload_video(
                video_file,
                "Test Title",
                "Test Description",
                ["tag1"],
                "public",
            )
        assert "auth refresh failed" in str(exc_info.value).lower()

    def test_upload_video_raises_when_youtube_client_init_fails(
        self, tmp_path, monkeypatch, mock_google_api
    ):
        """ทดสอบว่า upload_video raise YoutubeApiError เมื่อสร้าง YouTube client ไม่สำเร็จ"""
        video_file = tmp_path / "test.mp4"
        video_file.write_bytes(b"fake video")

        monkeypatch.setenv("YOUTUBE_CLIENT_ID", "test_id")
        monkeypatch.setenv("YOUTUBE_CLIENT_SECRET", "test_secret")
        monkeypatch.setenv("YOUTUBE_REFRESH_TOKEN", "test_token")

        # Make build raise an error
        mock_google_api["build"].side_effect = Exception("Build failed")

        with pytest.raises(YoutubeApiError) as exc_info:
            upload_video(
                video_file,
                "Test Title",
                "Test Description",
                ["tag1"],
                "public",
            )
        assert "client initialization failed" in str(exc_info.value).lower()

    def test_upload_video_raises_when_api_request_fails_with_http_error(
        self, tmp_path, monkeypatch, mock_google_api
    ):
        """ทดสอบว่า upload_video raise YoutubeApiError พร้อม status code เมื่อเกิด HttpError"""
        video_file = tmp_path / "test.mp4"
        video_file.write_bytes(b"fake video")

        monkeypatch.setenv("YOUTUBE_CLIENT_ID", "test_id")
        monkeypatch.setenv("YOUTUBE_CLIENT_SECRET", "test_secret")
        monkeypatch.setenv("YOUTUBE_REFRESH_TOKEN", "test_token")

        # Setup mocks
        mock_youtube = Mock()
        mock_request = Mock()
        mock_youtube.videos().insert.return_value = mock_request
        mock_google_api["build"].return_value = mock_youtube

        # Create a mock HttpError with status
        http_error = mock_google_api["HttpError"]("HTTP Error")
        http_error.resp = Mock(status=403)
        mock_request.execute.side_effect = http_error

        with pytest.raises(YoutubeApiError) as exc_info:
            upload_video(
                video_file,
                "Test Title",
                "Test Description",
                ["tag1"],
                "public",
            )
        assert exc_info.value.status == 403
        assert "api request failed" in str(exc_info.value).lower()

    def test_upload_video_raises_when_response_missing_video_id(
        self, tmp_path, monkeypatch, mock_google_api
    ):
        """ทดสอบว่า upload_video raise YoutubeApiError เมื่อ response ขาด video id"""
        video_file = tmp_path / "test.mp4"
        video_file.write_bytes(b"fake video")

        monkeypatch.setenv("YOUTUBE_CLIENT_ID", "test_id")
        monkeypatch.setenv("YOUTUBE_CLIENT_SECRET", "test_secret")
        monkeypatch.setenv("YOUTUBE_REFRESH_TOKEN", "test_token")

        mock_youtube = Mock()
        mock_request = Mock()
        mock_request.execute.return_value = {}  # Missing 'id' field
        mock_youtube.videos().insert.return_value = mock_request
        mock_google_api["build"].return_value = mock_youtube

        with pytest.raises(YoutubeApiError) as exc_info:
            upload_video(
                video_file,
                "Test Title",
                "Test Description",
                ["tag1"],
                "public",
            )
        assert "missing video id" in str(exc_info.value).lower()

    def test_upload_video_raises_when_response_video_id_empty(
        self, tmp_path, monkeypatch, mock_google_api
    ):
        """ทดสอบว่า upload_video raise YoutubeApiError เมื่อ video id เป็นสตริงว่าง"""
        video_file = tmp_path / "test.mp4"
        video_file.write_bytes(b"fake video")

        monkeypatch.setenv("YOUTUBE_CLIENT_ID", "test_id")
        monkeypatch.setenv("YOUTUBE_CLIENT_SECRET", "test_secret")
        monkeypatch.setenv("YOUTUBE_REFRESH_TOKEN", "test_token")

        mock_youtube = Mock()
        mock_request = Mock()
        mock_request.execute.return_value = {"id": ""}  # Empty string
        mock_youtube.videos().insert.return_value = mock_request
        mock_google_api["build"].return_value = mock_youtube

        with pytest.raises(YoutubeApiError) as exc_info:
            upload_video(
                video_file,
                "Test Title",
                "Test Description",
                ["tag1"],
                "public",
            )
        assert "missing video id" in str(exc_info.value).lower()


class TestUploadVideoSuccessFlow:
    """ทดสอบการทำงานปกติของ upload_video"""

    def test_upload_video_success_returns_video_id(
        self, tmp_path, monkeypatch, mock_google_api
    ):
        """ทดสอบว่า upload_video คืน video id เมื่ออัปโหลดสำเร็จ"""
        video_file = tmp_path / "test.mp4"
        video_file.write_bytes(b"fake video content")

        monkeypatch.setenv("YOUTUBE_CLIENT_ID", "test_id")
        monkeypatch.setenv("YOUTUBE_CLIENT_SECRET", "test_secret")
        monkeypatch.setenv("YOUTUBE_REFRESH_TOKEN", "test_token")

        mock_youtube = Mock()
        mock_request = Mock()
        mock_request.execute.return_value = {"id": "abc123xyz"}
        mock_youtube.videos().insert.return_value = mock_request
        mock_google_api["build"].return_value = mock_youtube

        result = upload_video(
            video_file,
            "Test Title",
            "Test Description",
            ["tag1", "tag2"],
            "public",
        )

        assert result == "abc123xyz"
        # Verify MediaFileUpload was called with correct parameters
        mock_google_api["MediaFileUpload"].assert_called_once_with(
            str(video_file), mimetype="video/mp4", resumable=True
        )

    def test_upload_video_passes_correct_body_to_api(
        self, tmp_path, monkeypatch, mock_google_api
    ):
        """ทดสอบว่า upload_video ส่ง request body ที่ถูกต้องไปยัง YouTube API"""
        video_file = tmp_path / "test.mp4"
        video_file.write_bytes(b"fake video")

        monkeypatch.setenv("YOUTUBE_CLIENT_ID", "test_id")
        monkeypatch.setenv("YOUTUBE_CLIENT_SECRET", "test_secret")
        monkeypatch.setenv("YOUTUBE_REFRESH_TOKEN", "test_token")

        mock_youtube = Mock()
        mock_request = Mock()
        mock_request.execute.return_value = {"id": "test_id"}
        mock_youtube.videos().insert.return_value = mock_request
        mock_google_api["build"].return_value = mock_youtube

        upload_video(
            video_file,
            "My Title",
            "My Description",
            ["dharma", "meditation"],
            "unlisted",
        )

        # Verify the API was called with correct body
        call_args = mock_youtube.videos().insert.call_args
        assert call_args.kwargs["part"] == "snippet,status"
        body = call_args.kwargs["body"]
        assert body["snippet"]["title"] == "My Title"
        assert body["snippet"]["description"] == "My Description"
        assert body["snippet"]["tags"] == ["dharma", "meditation"]
        assert body["status"]["privacyStatus"] == "unlisted"
