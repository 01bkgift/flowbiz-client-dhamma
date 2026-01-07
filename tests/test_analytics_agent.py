
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from pathlib import Path
import sys

# Add src to python path for testing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agents.analytics_agent.agent import AnalyticsAgent
from agents.analytics_agent.model import AnalyticsInput, AnalyticsOutput
from agents.analytics_agent.adapter import YouTubeAnalyticsAdapter
from agents.analytics_agent.mock import MockYouTubeAnalyticsAdapter

class TestAnalyticsAgent:
    
    @pytest.fixture
    def mock_adapter(self):
        return MockYouTubeAnalyticsAdapter()
        
    @pytest.fixture
    def agent(self, mock_adapter):
        return AnalyticsAgent(adapter=mock_adapter)

    def test_agent_initialization(self, agent):
        assert agent.name == "AnalyticsAgent"
        assert agent.adapter is not None

    def test_run_with_mock_data(self, agent):
        input_data = AnalyticsInput(date_range="30d")
        result = agent.run(input_data)
        
        assert isinstance(result, AnalyticsOutput)
        assert result.total_views > 0
        assert len(result.top_videos) > 0
        assert len(result.daily_stats) > 0

    def test_date_range_parsing_7d(self, agent):
        start, end = agent._parse_date_range("7d")
        
        start_date = datetime.strptime(start, "%Y-%m-%d")
        end_date = datetime.strptime(end, "%Y-%m-%d")
        diff = (end_date - start_date).days
        
        assert diff == 7

    def test_date_range_parsing_custom(self, agent):
        start, end = agent._parse_date_range("2025-01-01:2025-01-31")
        assert start == "2025-01-01"
        assert end == "2025-01-31"

    @patch("agents.analytics_agent.adapter.YouTubeAnalyticsAdapter")
    def test_run_with_real_adapter_mocked(self, MockAdapterClass):
        # This tests the agent logic with a mocked "Real" adapter structure
        # ensuring the logic in run() handles the specific dictionary structure correctly
        
        mock_instance = MockAdapterClass.return_value
        
        # Mock Channel Stats Response
        mock_instance.get_channel_stats.return_value = {
            "rows": [
                ["2025-01-01", 100, 500, 2, 0],
                ["2025-01-02", 200, 600, 3, 1]
            ]
        }
        
        # Mock Recent Videos Response (Batch Style)
        # agent.run() calls get_recent_videos() which returns List[Dict]
        # We need to mock what get_recent_videos returns
        
        mock_instance.get_recent_videos.return_value = [
            {
                "id": "vid1",
                "snippet": {
                    "title": "Video 1", 
                    "publishedAt": "2025-01-01T10:00:00Z"
                },
                "statistics": {
                    "viewCount": "1000",
                    "likeCount": "50", 
                    "commentCount": "10"
                }
            }
        ]
        
        agent = AnalyticsAgent(adapter=mock_instance)
        result = agent.run(AnalyticsInput(date_range="7d"))
        
        assert result.total_views == 300 # 100 + 200
        assert result.total_subscribers_gained == 4 # (2-0) + (3-1) = 2+2=4
        assert len(result.top_videos) == 1
        assert result.top_videos[0].video_id == "vid1"
