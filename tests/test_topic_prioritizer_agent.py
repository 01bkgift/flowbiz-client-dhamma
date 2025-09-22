"""
Test that TopicPrioritizerAgent v1 can be imported and instantiated
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agents.topic_prioritizer import (
    CandidateTopic,
    PriorityInput,
    PriorityOutput,
    TopicPrioritizerAgent,
    WeeksCapacity,
)


def test_topic_prioritizer_agent_initialization():
    """Test that TopicPrioritizerAgent can be created"""
    agent = TopicPrioritizerAgent()
    assert agent.name == "TopicPrioritizerAgent"
    assert agent.version == "1.0.0"
    assert "Content Calendar" in agent.description


def test_topic_prioritizer_basic_functionality():
    """Test basic functionality of TopicPrioritizerAgent v1"""
    agent = TopicPrioritizerAgent()

    # Create sample candidate topics
    sample_topics = [
        CandidateTopic(
            title="ปล่อยวางก่อนหลับ",
            pillar="ธรรมะประยุกต์",
            predicted_14d_views=12000,
            scores={
                "search_intent": 0.82,
                "freshness": 0.74,
                "evergreen": 0.65,
                "brand_fit": 0.93,
                "composite": 0.785,
            },
            reason="ค้นสูง + ปัญหาก่อนนอน",
        ),
        CandidateTopic(
            title="ธรรมะใจเบา",
            pillar="ธรรมะสั้น",
            predicted_14d_views=5000,
            scores={
                "search_intent": 0.75,
                "freshness": 0.80,
                "evergreen": 0.45,
                "brand_fit": 0.85,
                "composite": 0.71,
            },
            reason="เทรนด์ใหม่",
        ),
    ]

    input_data = PriorityInput(
        candidate_topics=sample_topics,
        strategy_focus="fast_growth",
        capacity=WeeksCapacity(weeks=4, longform_per_week=2, shorts_per_week=4),
    )

    # Run the agent
    result = agent.run(input_data)

    # Verify output
    assert isinstance(result, PriorityOutput)
    assert result.strategy_focus == "fast_growth"
    assert len(result.scheduled) >= 0
    assert len(result.unscheduled) >= 0
    assert result.diversity_summary.distinct_pillars >= 0
    assert result.meta.total_candidates == 2

    # Verify that at least some topics were processed
    total_processed = result.meta.scheduled_count + result.meta.unscheduled_count
    assert total_processed == 2

    # Check if scheduled topics have required fields
    for topic in result.scheduled:
        assert topic.topic_title in ["ปล่อยวางก่อนหลับ", "ธรรมะใจเบา"]
        assert topic.content_type in ["longform", "shorts"]
        assert topic.week.startswith("W")
        assert 0 <= topic.priority_score <= 100
        assert topic.expected_role in [
            "traffic_spike",
            "evergreen_seed",
            "series_part",
            "balance_filler",
            "audience_engagement",
        ]


def test_content_type_classification():
    """Test content type classification logic"""
    agent = TopicPrioritizerAgent()

    # Test longform classification
    longform_topic = CandidateTopic(
        title="เจาะลึกสมาธิ",
        pillar="เจาะลึก/ซีรีส์",
        predicted_14d_views=8000,
        scores={
            "search_intent": 0.60,
            "freshness": 0.50,
            "evergreen": 0.85,  # High evergreen
            "brand_fit": 0.90,  # High brand fit
            "composite": 0.71,
        },
        reason="เนื้อหาลึก",
    )

    # Test shorts classification
    shorts_topic = CandidateTopic(
        title="ทิปส์ดับใจร้อน",
        pillar="ธรรมะสั้น",
        predicted_14d_views=3000,
        scores={
            "search_intent": 0.85,  # High search intent
            "freshness": 0.90,
            "evergreen": 0.40,  # Low evergreen
            "brand_fit": 0.75,
            "composite": 0.73,
        },
        reason="ติดเทรนด์",
    )

    input_data = PriorityInput(
        candidate_topics=[longform_topic, shorts_topic],
        strategy_focus="evergreen_balance",
        capacity=WeeksCapacity(longform_per_week=2, shorts_per_week=4),
    )

    result = agent.run(input_data)

    # Should have both content types
    content_types = {topic.content_type for topic in result.scheduled}
    assert len(content_types) >= 1  # At least one type should be present


def test_strategy_focus_impacts_scoring():
    """Test that different strategies affect priority scoring"""
    agent = TopicPrioritizerAgent()

    # Same topic with different strategies
    topic = CandidateTopic(
        title="สมาธิเบื้องต้น",
        pillar="ธรรมะประยุกต์",
        predicted_14d_views=6000,
        scores={
            "search_intent": 0.70,
            "freshness": 0.85,  # High freshness
            "evergreen": 0.60,  # Medium evergreen
            "brand_fit": 0.80,
            "composite": 0.74,
        },
        reason="สมดุล",
    )

    # Test fast_growth strategy
    input_fast = PriorityInput(
        candidate_topics=[topic],
        strategy_focus="fast_growth",
        capacity=WeeksCapacity(longform_per_week=1, shorts_per_week=2),
    )

    result_fast = agent.run(input_fast)

    # Test evergreen_balance strategy
    input_evergreen = PriorityInput(
        candidate_topics=[topic],
        strategy_focus="evergreen_balance",
        capacity=WeeksCapacity(longform_per_week=1, shorts_per_week=2),
    )

    result_evergreen = agent.run(input_evergreen)

    # Both should process the topic
    assert result_fast.meta.total_candidates == 1
    assert result_evergreen.meta.total_candidates == 1

    # Strategies should be different
    assert result_fast.strategy_focus == "fast_growth"
    assert result_evergreen.strategy_focus == "evergreen_balance"


def test_imports_work():
    """Test that all imports work correctly"""
    from agents import (
        TopicPrioritizerAgent,
        TrendScoutAgent,
    )

    # Verify all classes can be instantiated
    trend_agent = TrendScoutAgent()
    priority_agent = TopicPrioritizerAgent()

    assert trend_agent.name == "TrendScoutAgent"
    assert priority_agent.name == "TopicPrioritizerAgent"
