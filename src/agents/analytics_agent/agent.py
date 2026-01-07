from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from automation_core.base_agent import BaseAgent
from .model import AnalyticsInput, AnalyticsOutput, VideoStats, DailyStat
from .adapter import YouTubeAnalyticsAdapter

class AnalyticsAgent(BaseAgent[AnalyticsInput, AnalyticsOutput]):
    """
    Agent for fetching and analyzing YouTube Channel Performance.
    """
    
    def __init__(self, adapter: Optional[YouTubeAnalyticsAdapter] = None):
        super().__init__(
            name="AnalyticsAgent",
            version="1.0.0",
            description="Fetches and analyzes YouTube channel KPI data"
        )
        self.adapter = adapter

    def _parse_date_range(self, date_range: str):
        """Parse date range string into start and end dates (YYYY-MM-DD)"""
        today = datetime.now()
        
        if date_range == "7d":
            start_date = today - timedelta(days=7)
            end_date = today
        elif date_range == "30d":
            start_date = today - timedelta(days=30)
            end_date = today
        elif date_range == "90d":
            start_date = today - timedelta(days=90)
            end_date = today
        elif ":" in date_range:
            start_str, end_str = date_range.split(":")
            return start_str, end_str
        else:
            # Default to 30d
            start_date = today - timedelta(days=30)
            end_date = today
            
        return start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")

    def run(self, input_data: AnalyticsInput) -> AnalyticsOutput:
        """Run the analysis"""
        if not self.adapter:
            raise RuntimeError("Adapter not initialized")
            
        start_date, end_date = self._parse_date_range(input_data.date_range)
        
        # 1. Fetch Daily Stats (Views, Subs, Watch Time)
        report = self.adapter.get_channel_stats(start_date, end_date)
        
        total_views = 0
        total_watch_minutes = 0
        total_subs_gained = 0
        daily_stats = []
        
        if "rows" in report:
            for row in report["rows"]:
                # API returns [day, views, estimatedMinutesWatched, subscribersGained, subscribersLost]
                day, views, watch_min, subs_gain, subs_lost = row
                
                daily_stats.append(DailyStat(
                    date=day,
                    views=int(views),
                    estimated_minutes_watched=int(watch_min),
                    subscribers_gained=int(subs_gain),
                    subscribers_lost=int(subs_lost)
                ))
                
                total_views += int(views)
                total_watch_minutes += int(watch_min)
                total_subs_gained += (int(subs_gain) - int(subs_lost))

        # 2. Fetch Top Videos (Recent 10)
        recent_videos = self.adapter.get_recent_videos(max_results=10)
        top_videos = []
        
        for vid in recent_videos:
            snippet = vid["snippet"]
            stats = vid["statistics"]
            
            published_at_str = snippet.get("publishedAt")
            if not published_at_str:
                print(f"⚠️ WARNING: Skipping video {vid.get('id')} due to missing 'publishedAt' field.")
                continue

            top_videos.append(VideoStats(
                video_id=vid.get("id", ""),
                title=snippet.get("title", "Unknown"),
                published_at=datetime.strptime(published_at_str, "%Y-%m-%dT%H:%M:%SZ"),
                views=int(stats.get("viewCount", 0)),
                likes=int(stats.get("likeCount", 0)),
                comments=int(stats.get("commentCount", 0))
            ))
            
        # 3. Sort by views
        top_videos.sort(key=lambda x: x.views, reverse=True)
        
        return AnalyticsOutput(
            start_date=start_date,
            end_date=end_date,
            total_views=total_views,
            total_watch_time_minutes=total_watch_minutes,
            total_subscribers_gained=total_subs_gained,
            top_videos=top_videos,
            daily_stats=daily_stats
        )
