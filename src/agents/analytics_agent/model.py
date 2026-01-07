from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

class VideoStats(BaseModel):
    """Statistics for a single video"""
    video_id: str
    title: str
    published_at: datetime
    views: int = 0
    likes: int = 0
    comments: int = 0
    average_view_duration_seconds: float = 0.0
    estimated_minutes_watched: int = 0

class DailyStat(BaseModel):
    """Daily channel statistics"""
    date: str
    views: int
    estimated_minutes_watched: int
    subscribers_gained: int
    subscribers_lost: int

class AnalyticsInput(BaseModel):
    """Input for Analytics Agent"""
    date_range: str = Field(
        default="30d", 
        description="Date range shortcut (7d, 30d, 90d) or custom range (YYYY-MM-DD:YYYY-MM-DD)"
    )

class AnalyticsOutput(BaseModel):
    """Output from Analytics Agent"""
    generated_at: datetime = Field(default_factory=datetime.now)
    start_date: str
    end_date: str
    total_views: int
    total_watch_time_minutes: int
    total_subscribers_gained: int
    top_videos: List[VideoStats] = []
    daily_stats: List[DailyStat] = []
