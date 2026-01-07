#!/usr/bin/env python3
"""
YouTube Auto Uploader
Upload videos to YouTube using YouTube Data API v3

Setup:
1. Create Google Cloud Project
2. Enable YouTube Data API v3
3. Create OAuth 2.0 credentials
4. Download client_secret.json
"""

import json
from pathlib import Path

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
except ImportError:
    print("❌ Required libraries not installed")
    print(
        "💡 Run: pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client"
    )
    exit(1)


# YouTube API scopes
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


class YouTubeUploader:
    """Auto upload videos to YouTube"""

    def __init__(self, production_dir: Path):
        self.production_dir = Path(production_dir)
        self.youtube = None

        # Load production data
        self.metadata = self._load_json("metadata.json")
        self.seo_data = self._load_json("seo_metadata.json")

        # Credentials
        self.credentials_file = Path("youtube_client_secret.json")
        self.token_file = Path("youtube_token.json")

    def _load_json(self, filename: str) -> dict:
        """Load JSON file"""
        filepath = self.production_dir / filename
        if not filepath.exists():
            print(f"⚠️  {filename} not found")
            return {}

        with open(filepath, encoding="utf-8") as f:
            return json.load(f)

    def authenticate(self) -> bool:
        """Authenticate with YouTube API"""
        try:
            creds = None

            # Load existing token (JSON only)
            if self.token_file.exists():
                try:
                    creds = Credentials.from_authorized_user_file(
                        str(self.token_file), SCOPES
                    )
                except ValueError:
                    # หากไฟล์ token เสียหาย ให้ดำเนินการ re-authenticate
                    creds = None

            # Refresh if expired
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())

            # New login if no valid credentials
            if not creds or not creds.valid:
                if not self.credentials_file.exists():
                    print(f"❌ Credentials file not found: {self.credentials_file}")
                    print("💡 Download from Google Cloud Console:")
                    print("   1. Go to https://console.cloud.google.com")
                    print("   2. APIs & Services → Credentials")
                    print("   3. Create OAuth 2.0 Client → Download JSON")
                    print(f"   4. Save as: {self.credentials_file}")
                    return False

                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_file), SCOPES
                )
                creds = flow.run_local_server(port=0)

                # Save token as JSON
                with open(self.token_file, "w") as token:
                    token.write(creds.to_json())

            # Build YouTube service
            self.youtube = build("youtube", "v3", credentials=creds)

            print("✅ Authenticated with YouTube API")
            return True

        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return False

    def prepare_metadata(self) -> dict:
        """Prepare video metadata for upload"""
        # Get data
        title = self.metadata.get("title", "Untitled Dhamma Video")

        # Build description
        description = self._build_description()

        # Get tags
        tags = self.seo_data.get("tags", [])
        if not tags:
            tags = ["ธรรมะ", "พระพุทธศาสนา", "meditation", "buddhism"]

        # Category (22 = People & Blogs, 27 = Education)
        category_id = "27"  # Education

        return {
            "snippet": {
                "title": title[:100],  # YouTube limit
                "description": description[:5000],  # YouTube limit
                "tags": tags[:30],  # Max 30 tags
                "categoryId": category_id,
                "defaultLanguage": "th",
                "defaultAudioLanguage": "th",
            },
            "status": {
                "privacyStatus": "public",  # or "private", "unlisted"
                "selfDeclaredMadeForKids": False,
                "publicStatsViewable": True,
            },
        }

    def _build_description(self) -> str:
        """Build YouTube description"""
        title = self.metadata.get("title", "")

        # Template
        description = f"🙏 {title}\n\n"

        # Add summary if available
        if "description" in self.seo_data:
            description += f"{self.seo_data['description']}\n\n"

        # Add sections
        description += "📖 ในวิดีโอนี้คุณจะได้เรียนรู้:\n"

        # Add key points
        voiceover_guide = self._load_json("voiceover_guide.json")
        sections = voiceover_guide.get("sections", [])

        for i, section in enumerate(sections[:5], 1):
            section_title = section.get("title", f"Section {i}")
            description += f"✓ {section_title}\n"

        description += "\n"

        # Add timestamps
        description += "⏰ Timestamps:\n"
        for section in sections[:10]:
            timestamp = section.get("timestamp", "00:00")
            section_title = section.get("title", "Section")
            description += f"{timestamp} - {section_title}\n"

        description += "\n"

        # CTA
        description += "🔔 Subscribe เพื่อรับธรรมะใหม่ๆ ทุกสัปดาห์\n"
        description += "👍 กด Like ถ้าชอบวิดีโอนี้\n"
        description += "💬 แชร์ความคิดเห็นด้านล่างได้เลย\n\n"

        # Tags section
        description += "#ธรรมะ #พระพุทธศาสนา #meditation #mindfulness\n"

        return description

    def upload(
        self, video_file: Path, thumbnail_file: Path | None = None
    ) -> str | None:
        """Upload video to YouTube"""
        try:
            if not video_file.exists():
                print(f"❌ Video file not found: {video_file}")
                return None

            print(f"\n📤 Uploading video: {video_file.name}")
            print(f"📊 Size: {video_file.stat().st_size / (1024 * 1024):.1f} MB")

            # Prepare metadata
            body = self.prepare_metadata()

            print(f"\n📝 Title: {body['snippet']['title']}")
            print(f"🏷️  Tags: {', '.join(body['snippet']['tags'][:5])}...")
            print(f"🔒 Privacy: {body['status']['privacyStatus']}")

            # Create media upload
            media = MediaFileUpload(
                str(video_file),
                chunksize=1024 * 1024,  # 1 MB chunks
                resumable=True,
                mimetype="video/mp4",
            )

            # Upload request
            request = self.youtube.videos().insert(
                part=",".join(body.keys()), body=body, media_body=media
            )

            # Execute upload
            print("\n🚀 Uploading...")
            response = None

            while response is None:
                status, response = request.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    print(f"   Uploaded {progress}%", end="\r")

            print("   Uploaded 100%")

            # Get video ID
            video_id = response["id"]
            video_url = f"https://www.youtube.com/watch?v={video_id}"

            print("\n✅ Video uploaded successfully!")
            print(f"🔗 URL: {video_url}")
            print(f"🆔 Video ID: {video_id}")

            # Upload thumbnail if provided
            if thumbnail_file and thumbnail_file.exists():
                self._upload_thumbnail(video_id, thumbnail_file)

            return video_id

        except Exception as e:
            print(f"❌ Upload error: {e}")
            return None

    def _upload_thumbnail(self, video_id: str, thumbnail_file: Path) -> bool:
        """Upload custom thumbnail"""
        try:
            print(f"\n🖼️  Uploading thumbnail: {thumbnail_file.name}")

            request = self.youtube.thumbnails().set(
                videoId=video_id, media_body=MediaFileUpload(str(thumbnail_file))
            )

            request.execute()

            print("✅ Thumbnail uploaded")
            return True

        except Exception as e:
            print(f"⚠️  Thumbnail upload error: {e}")
            return False

    def process(
        self, video_file: Path, thumbnail_file: Path | None = None
    ) -> str | None:
        """Complete upload process"""
        print("\n" + "=" * 70)
        print("📤 YouTube Auto Uploader")
        print("=" * 70 + "\n")

        # Step 1: Authenticate
        print("🔐 Step 1/2: Authenticating...")
        if not self.authenticate():
            return None

        # Step 2: Upload
        print("\n📤 Step 2/2: Uploading video...")
        video_id = self.upload(video_file, thumbnail_file)

        if video_id:
            print("\n" + "=" * 70)
            print("✅ UPLOAD COMPLETED!")
            print("=" * 70)
            print(f"\n🔗 Video URL: https://www.youtube.com/watch?v={video_id}")
            print(f"🎬 Video ID: {video_id}")
            print("\n💡 Next steps:")
            print("   1. Add to playlist (YouTube Studio)")
            print("   2. Enable monetization (if eligible)")
            print("   3. Share on social media")

        return video_id


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="YouTube Auto Uploader")
    parser.add_argument("--production-dir", required=True, help="Production directory")
    parser.add_argument("--video", required=True, help="Video file to upload")
    parser.add_argument("--thumbnail", help="Thumbnail file (optional)")

    args = parser.parse_args()

    production_dir = Path(args.production_dir)
    video_file = Path(args.video)
    thumbnail_file = Path(args.thumbnail) if args.thumbnail else None

    # Validate
    if not production_dir.exists():
        print(f"❌ Production directory not found: {production_dir}")
        return 1

    if not video_file.exists():
        print(f"❌ Video file not found: {video_file}")
        return 1

    # Upload
    uploader = YouTubeUploader(production_dir)
    video_id = uploader.process(video_file, thumbnail_file)

    return 0 if video_id else 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
