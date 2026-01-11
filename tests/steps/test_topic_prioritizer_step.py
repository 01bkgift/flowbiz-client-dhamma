"""
Integration tests for TopicPrioritizerStep
"""

import json
import sys
from pathlib import Path

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from steps.topic_prioritizer import TopicPrioritizerStep


class TestTopicPrioritizerStep:
    """Test suite for TopicPrioritizerStep"""

    def test_step_initialization(self):
        """Test step can be instantiated"""
        step = TopicPrioritizerStep()
        assert step.step_id == "topic_prioritizer"
        assert step.step_type == "TopicPrioritizer"
        assert step.version == "1.0.0"

    def test_execute_with_mock_data(self, tmp_path):
        """Test execution with mock trend candidates"""
        # Create mock input file (TrendScout format)
        mock_data = {
            "topics": [
                {
                    "title": "ปล่อยวางก่อนหลับ",
                    "category": "ธรรมะประยุกต์",
                    "priority": 5,
                    "why_now": "ค้นหาสูง",
                    "keywords": ["mindfulness", "sleep"],
                },
                {
                    "title": "สมาธิเบื้องต้น",
                    "category": "ธรรมะสั้น",
                    "priority": 4,
                    "why_now": "เทรนด์ใหม่",
                    "keywords": ["meditation", "beginner"],
                },
            ]
        }

        input_file = tmp_path / "trend_candidates.json"
        input_file.write_text(json.dumps(mock_data, ensure_ascii=False), encoding="utf-8")

        step = TopicPrioritizerStep()
        result = step.execute({
            "input_file": str(input_file),
            "output_dir": str(tmp_path),
            "strategy_focus": "fast_growth",
            "weeks": 4,
            "longform_per_week": 2,
            "shorts_per_week": 4,
        })

        assert result["status"] == "success"
        assert "output_file" in result
        assert Path(result["output_file"]).exists()
        assert result["scheduled_count"] >= 0

    def test_execute_with_existing_mock_file(self):
        """Test with existing data/mock_topics.json"""
        mock_file = Path("data/mock_topics.json")
        if not mock_file.exists():
            pytest.skip("mock_topics.json not found")

        step = TopicPrioritizerStep()
        result = step.execute({
            "input_file": str(mock_file),
            "output_dir": "output/test_step",
            "strategy_focus": "evergreen_balance",
        })

        assert result["status"] == "success"
        assert result["scheduled_count"] > 0

    def test_all_strategies(self, tmp_path):
        """Test all three strategy options"""
        mock_data = {
            "topics": [
                {
                    "title": "Test Topic",
                    "category": "ธรรมะประยุกต์",
                    "priority": 5,
                    "why_now": "test",
                }
            ]
        }

        input_file = tmp_path / "trend_candidates.json"
        input_file.write_text(json.dumps(mock_data, ensure_ascii=False), encoding="utf-8")

        step = TopicPrioritizerStep()
        strategies = ["fast_growth", "evergreen_balance", "depth_series"]

        for strategy in strategies:
            result = step.execute({
                "input_file": str(input_file),
                "output_dir": str(tmp_path / strategy),
                "strategy_focus": strategy,
            })
            assert result["status"] == "success", f"Failed for strategy: {strategy}"
            assert result["strategy_focus"] == strategy

    def test_missing_input_file(self, tmp_path):
        """Test error handling for missing input file"""
        step = TopicPrioritizerStep()
        result = step.execute({
            "input_file": str(tmp_path / "nonexistent.json"),
            "output_dir": str(tmp_path),
        })

        assert result["status"] == "error"
        assert "not found" in result["error"]

    def test_empty_topics(self, tmp_path):
        """Test handling of empty topics list"""
        mock_data = {"topics": []}

        input_file = tmp_path / "empty.json"
        input_file.write_text(json.dumps(mock_data), encoding="utf-8")

        step = TopicPrioritizerStep()
        result = step.execute({
            "input_file": str(input_file),
            "output_dir": str(tmp_path),
        })

        assert result["status"] == "error"
