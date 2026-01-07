import os
import pickle
import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

class YouTubeAnalyticsAdapter:
    """Adapter for YouTube Analytics API"""
    
    SCOPES = [
        "https://www.googleapis.com/auth/yt-analytics.readonly",
        "https://www.googleapis.com/auth/youtube.readonly"
    ]
    
    def __init__(self, credentials_json: Path, token_pickle: Path):
        self.credentials_file = credentials_json
        self.token_file = token_pickle
        self.analytics = None
        self.youtube = None

    def authenticate(self) -> bool:
        """Authenticate with Google APIs"""
        creds = None
        
        # Load existing token
        if self.token_file.exists():
            try:
                # Try loading as JSON first (new format)
                from google.oauth2.credentials import Credentials
                creds = Credentials.from_authorized_user_file(str(self.token_file), self.SCOPES)
            except Exception:
                 # Fallback to pickle (migration path, but avoiding writes)
                with open(self.token_file, "rb") as token:
                    creds = pickle.load(token)
                
        # Refresh if valid but expired
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            
        # New login
        if not creds or not creds.valid:
            if not self.credentials_file.exists():
                print(f"❌ Credentials file not found: {self.credentials_file}")
                return False
                
            flow = InstalledAppFlow.from_client_secrets_file(
                str(self.credentials_file), self.SCOPES
            )
            creds = flow.run_local_server(port=0)
            
            # Save token as JSON (Safer)
            with open(self.token_file, "w") as token:
                token.write(creds.to_json())
                
        # Build services
        self.analytics = build("youtubeAnalytics", "v2", credentials=creds)
        self.youtube = build("youtube", "v3", credentials=creds)
        
        return True

    def get_channel_stats(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """Get aggregated channel statistics"""
        if not self.analytics:
            raise RuntimeError("Not authenticated")
            
        return self.analytics.reports().query(
            ids="channel==MINE",
            startDate=start_date,
            endDate=end_date,
            metrics="views,estimatedMinutesWatched,subscribersGained,subscribersLost",
            dimensions="day",
            sort="day"
        ).execute()

    def get_video_stats(self, video_id: str) -> Dict[str, Any]:
        """Get statistics for a specific video"""
        if not self.youtube:
            raise RuntimeError("Not authenticated")
            
        response = self.youtube.videos().list(
            part="snippet,statistics,contentDetails",
            id=video_id
        ).execute()
        
        if not response["items"]:
            return {}
            
        return response["items"][0]
        
    def get_recent_videos(self, max_results: int = 10) -> List[Dict[str, Any]]:
        """Get list of recent videos with their stats in a batch request."""
        if not self.youtube:
            raise RuntimeError("Not authenticated")
            
        search_response = self.youtube.search().list(
            part="snippet",
            forMine=True,
            type="video",
            order="date",
            maxResults=max_results
        ).execute()
        
        video_ids = [item["id"]["videoId"] for item in search_response.get("items", [])]
        
        if not video_ids:
            return []
            
        video_response = self.youtube.videos().list(
            part="snippet,statistics,contentDetails",
            id=",".join(video_ids)
        ).execute()
        
        return video_response.get("items", [])
