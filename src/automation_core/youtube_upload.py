"""ยูทิลิตี้สำหรับอัปโหลดวิดีโอขึ้น YouTube

โมดูลนี้ทำหน้าที่ห่อการเรียก YouTube Data API สำหรับการอัปโหลดวิดีโอ
โดยใช้ OAuth2 (refresh token) จากตัวแปรสภาพแวดล้อม และทำ lazy import
ของไลบรารี Google เพื่อไม่ให้กระทบส่วนอื่นของระบบในกรณีที่ยังไม่ติดตั้ง deps
"""

from __future__ import annotations

import hashlib
import json
import os
import unicodedata
from pathlib import Path

MOCK_VIDEO_ID_DRY_RUN = "soft-live-dry-run-video-id"
MOCK_VIDEO_ID_FALLBACK = "soft-live-fallback-dry-run-id"


def _normalize_title(title: str) -> str:
    """Normalize title for deterministic hashing.

    - Unicode NFKC normalization
    - Strip leading/trailing whitespace
    - Collapse internal whitespace to single space
    - Lowercase
    """
    # Unicode normalization
    normalized = unicodedata.normalize("NFKC", title)
    # Strip and collapse whitespace
    normalized = " ".join(normalized.split())
    # Lowercase
    return normalized.lower()


def _extract_content_fingerprint(run_dir: Path | None) -> str | None:
    """Extract content fingerprint from existing artifacts.

    Priority order:
    1. video_render_summary.json -> text_sha256_12
    2. metadata.json -> hash(title + description)
    3. script.json -> hash(entire script)

    Returns None if all artifacts missing (fallback to legacy behavior).
    """
    if run_dir is None:
        return None

    artifacts_dir = run_dir / "artifacts"
    if not artifacts_dir.exists():
        return None

    # Priority 1: video_render_summary.json
    render_summary = artifacts_dir / "video_render_summary.json"
    if render_summary.exists():
        try:
            with open(render_summary, encoding="utf-8") as f:
                data = json.load(f)
                if "text_sha256_12" in data:
                    return data["text_sha256_12"]
        except (json.JSONDecodeError, KeyError):
            pass

    # Priority 2: metadata.json
    metadata_file = artifacts_dir / "metadata.json"
    if metadata_file.exists():
        try:
            with open(metadata_file, encoding="utf-8") as f:
                data = json.load(f)
                # Hash title + description for content identity
                title = data.get("title", "")
                desc = data.get("description", "")
                if title or desc:
                    content = f"{title}|{desc}"
                    return hashlib.sha256(content.encode()).hexdigest()[:12]
        except Exception:
            pass

    # Priority 3: script.json
    script_file = artifacts_dir / "script.json"
    if script_file.exists():
        try:
            with open(script_file, encoding="utf-8") as f:
                data = json.load(f)
                # Hash entire script content
                script_str = json.dumps(data, sort_keys=True)
                return hashlib.sha256(script_str.encode()).hexdigest()[:12]
        except Exception:
            pass

    return None


def _generate_deterministic_fake_id(
    title: str, mode: str, run_dir: Path | None = None
) -> str:
    """Generate a collision-safe deterministic fake video ID.

    Uses content fingerprinting to prevent collisions when the same title
    is reused with different content.

    Args:
        title: Video title
        mode: Soft-Live mode (e.g., 'dry_run', 'unlisted')
        run_dir: Optional path to run directory for artifact access

    Returns:
        Fake video ID in format: soft-live-dry-{16-char-hex}
    """
    # Normalize title for consistent hashing
    normalized_title = _normalize_title(title)

    # Extract content fingerprint from artifacts (collision prevention)
    fingerprint = _extract_content_fingerprint(run_dir)

    # Build canonical payload
    payload = {
        "title": normalized_title,
        "mode": mode,
        "fingerprint": fingerprint,
    }

    # Deterministic JSON serialization
    payload_str = json.dumps(payload, sort_keys=True)

    # Generate stable digest
    digest = hashlib.sha256(payload_str.encode()).hexdigest()[:16]
    return f"soft-live-dry-{digest}"


class YoutubeUploadError(Exception):
    """ข้อผิดพลาดฐานสำหรับการอัปโหลดวิดีโอขึ้น YouTube"""


class YoutubeDepsMissingError(YoutubeUploadError):
    """เกิดเมื่อยังไม่ได้ติดตั้งไลบรารีที่จำเป็นสำหรับ Google API"""


class YoutubeAuthMissingError(YoutubeUploadError):
    """เกิดเมื่อขาดตัวแปรสภาพแวดล้อมที่ใช้สำหรับยืนยันตัวตน YouTube"""


class YoutubeApiError(YoutubeUploadError):
    """เกิดเมื่อ YouTube API ตอบกลับด้วยข้อผิดพลาดหรือ response ไม่ถูกต้อง"""

    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


def _require_env(name: str) -> str:
    """อ่านค่าตัวแปรสภาพแวดล้อมที่จำเป็น

    Args:
        name: ชื่อตัวแปรสภาพแวดล้อม

    Returns:
        ค่าที่ถูก trim แล้ว

    Raises:
        YoutubeAuthMissingError: เมื่อไม่มีตัวแปรหรือเป็นค่าว่าง
    """
    value = os.environ.get(name)
    if value is None or not value.strip():
        raise YoutubeAuthMissingError(
            f"Missing required YouTube auth environment variable: {name}"
        )
    return value.strip()


def upload_video(
    mp4_path: Path | str,
    title: str,
    description: str,
    tags: list[str],
    privacy_status: str,
) -> str:
    """อัปโหลดไฟล์วิดีโอขึ้น YouTube ด้วย YouTube Data API

    ฟังก์ชันนี้จะใช้ OAuth2 credentials จากตัวแปรสภาพแวดล้อม
    `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REFRESH_TOKEN`
    เพื่อรีเฟรชโทเคนและสร้าง client สำหรับเรียก YouTube API

    Args:
        mp4_path: พาธไปยังไฟล์วิดีโอ MP4 ที่ต้องการอัปโหลด
        title: ชื่อเรื่องของวิดีโอ
        description: คำอธิบายของวิดีโอ
        tags: รายการแท็ก (string) สำหรับวิดีโอ
        privacy_status: สถานะความเป็นส่วนตัวของวิดีโอ (`public`, `unlisted`, `private`)

    Returns:
        YouTube video id หลังอัปโหลดสำเร็จ

    Raises:
        YoutubeDepsMissingError: เมื่อยังไม่ได้ติดตั้ง google-auth/google-api-python-client
        YoutubeAuthMissingError: เมื่อขาดตัวแปรสภาพแวดล้อมสำหรับยืนยันตัวตน
        YoutubeUploadError: เมื่อพารามิเตอร์อินพุตไม่ถูกต้อง (เช่น ไฟล์ไม่พบ)
        YoutubeApiError: เมื่อเกิดข้อผิดพลาดจาก YouTube API
    """
    if not isinstance(mp4_path, Path):
        mp4_path = Path(mp4_path)
    if not mp4_path.exists():
        raise YoutubeUploadError(f"Video file does not exist: {mp4_path}")
    if not mp4_path.is_file():
        raise YoutubeUploadError(f"Video path is not a file: {mp4_path}")

    if not isinstance(title, str) or not title.strip():
        raise YoutubeUploadError("Video title must be a non-empty string")
    if not isinstance(description, str) or not description.strip():
        raise YoutubeUploadError("Video description must be a non-empty string")

    allowed_privacy_statuses = {"private", "unlisted", "public"}
    if (
        not isinstance(privacy_status, str)
        or privacy_status not in allowed_privacy_statuses
    ):
        raise YoutubeUploadError(
            "privacy_status must be one of: "
            + ", ".join(sorted(allowed_privacy_statuses))
        )

    # --- SOFT-LIVE ENFORCEMENT START ---
    soft_live_enabled = (
        os.environ.get("SOFT_LIVE_ENABLED", "true").strip().lower() == "true"
    )

    if soft_live_enabled:
        soft_live_mode = (
            os.environ.get("SOFT_LIVE_YOUTUBE_MODE", "dry_run").strip().lower()
        )
        print(f"[Soft-Live] Soft-Live Enabled. Mode: {soft_live_mode}")

        if soft_live_mode == "dry_run":
            print("[Soft-Live] Enforcing dry_run. Upload skipped.")
            print(f"[Soft-Live] Mocking upload for: {title} ({privacy_status})")
            # Derive run_dir from mp4_path for content fingerprinting
            # Pattern: output/<run_id>/artifacts/video.mp4
            run_dir = None
            try:
                artifacts_idx = mp4_path.parts.index("artifacts")
                if artifacts_idx > 0:
                    run_dir = Path(*mp4_path.parts[:artifacts_idx])
            except ValueError:
                # "artifacts" is not in the path, run_dir remains None.
                pass
            return _generate_deterministic_fake_id(title, "dry_run", run_dir)

        # Map modes to severity: private=0, unlisted=1, public=2
        severity_map = {"private": 0, "unlisted": 1, "public": 2}

        # Validate configured mode - STRICT: public is NOT allowed for Soft-Live
        if soft_live_mode == "public":
            print(
                "[Soft-Live] SAFETY VIOLATION: 'public' is not allowed in Soft-Live mode!"
            )
            # If fail_closed is True (default logic of caller), this is critical.
            # Here we enforce fallback to dry_run as immediate safety net if code reached here.
            return MOCK_VIDEO_ID_FALLBACK

        if soft_live_mode not in severity_map:
            # Default to dry_run logic if invalid config in Soft-Live
            print(f"[Soft-Live] Invalid mode '{soft_live_mode}'. Fallback to dry_run.")
            return MOCK_VIDEO_ID_FALLBACK

        current_severity = severity_map.get(
            privacy_status, 2
        )  # default to public if unknown
        enforced_severity = severity_map[soft_live_mode]

        if current_severity > enforced_severity:
            print(f"[Soft-Live] OVERRIDE: {privacy_status} -> {soft_live_mode}")
            privacy_status = soft_live_mode
        else:
            print(
                f"[Soft-Live] Privacy status '{privacy_status}' is compliant with '{soft_live_mode}'."
            )
    # --- SOFT-LIVE ENFORCEMENT END ---

    try:
        from google.auth.exceptions import RefreshError
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        from googleapiclient.errors import HttpError
        from googleapiclient.http import MediaFileUpload
    except ImportError as exc:
        raise YoutubeDepsMissingError(
            "Google API dependencies are not installed"
        ) from exc

    client_id = _require_env("YOUTUBE_CLIENT_ID")
    client_secret = _require_env("YOUTUBE_CLIENT_SECRET")
    refresh_token = _require_env("YOUTUBE_REFRESH_TOKEN")

    scopes = ["https://www.googleapis.com/auth/youtube.upload"]
    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=scopes,
    )

    try:
        creds.refresh(Request())
    except RefreshError as exc:
        raise YoutubeApiError("YouTube auth refresh failed") from exc

    try:
        youtube = build("youtube", "v3", credentials=creds)
    except (KeyboardInterrupt, SystemExit):
        raise
    except HttpError as exc:
        status = getattr(getattr(exc, "resp", None), "status", None)
        raise YoutubeApiError(
            "YouTube client initialization failed",
            status=status,
        ) from exc
    except (OSError, ValueError, TypeError) as exc:
        raise YoutubeApiError("YouTube client initialization failed") from exc
    except Exception as exc:
        raise YoutubeApiError("YouTube client initialization failed") from exc

    string_tags = [tag for tag in tags if isinstance(tag, str)] if tags else []
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": string_tags,
        },
        "status": {
            "privacyStatus": privacy_status,
        },
    }

    media = MediaFileUpload(str(mp4_path), mimetype="video/mp4", resumable=True)
    request = youtube.videos().insert(
        part="snippet,status", body=body, media_body=media
    )
    try:
        response = request.execute()
    except HttpError as exc:
        status = getattr(getattr(exc, "resp", None), "status", None)
        raise YoutubeApiError("YouTube API request failed", status=status) from exc
    except (KeyboardInterrupt, SystemExit):
        raise
    except Exception as exc:
        raise YoutubeApiError("YouTube upload failed") from exc

    video_id = None
    if isinstance(response, dict):
        video_id = response.get("id")

    if not isinstance(video_id, str) or not video_id:
        raise YoutubeApiError("YouTube API response missing video id")

    return video_id
