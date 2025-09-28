"""Tests for PersonalizationAgent"""

from datetime import date, timedelta
from unittest.mock import patch

from agents.personalization import (  # noqa: E402
    EngagementMetrics,
    PersonalizationAgent,
    PersonalizationConfig,
    PersonalizationInput,
    PersonalizationRequest,
    PersonalizedRecommendation,
    TrendInterest,
    UserProfile,
    ViewHistoryItem,
)

FIXED_TODAY = date(2025, 1, 15)


def _set_fixed_today(mock_date) -> None:
    mock_date.today.return_value = FIXED_TODAY
    mock_date.side_effect = lambda *args, **kwargs: date(*args, **kwargs)


def _build_sample_request(today: date = FIXED_TODAY) -> PersonalizationInput:
    request = PersonalizationRequest(
        user_id="U001",
        profile=UserProfile(
            age=28,
            gender="female",
            location="Bangkok",
            interest=["นอนหลับ", "สมาธิ", "สุขภาพจิต"],
        ),
        view_history=[
            ViewHistoryItem(
                video_id="V05",
                title="สมาธิก่อนนอน",
                watched_pct=95,
                date=today - timedelta(days=1),
            ),
            ViewHistoryItem(
                video_id="V04",
                title="สมาธิสั้น",
                watched_pct=88,
                date=today - timedelta(days=10),
            ),
        ],
        engagement=EngagementMetrics(like=8, comment=2, share=1),
        trend=[
            TrendInterest(topic="นอนหลับ", score=92),
            TrendInterest(topic="สมาธิ", score=85),
        ],
        config=PersonalizationConfig(recommend_top_n=3, min_confidence_pct=70),
    )
    return PersonalizationInput(personalization_request=request)


def test_personalization_agent_initialization():
    """Ensure agent metadata is set"""

    agent = PersonalizationAgent()
    assert agent.name == "PersonalizationAgent"
    assert agent.version == "1.0.0"
    assert "คำแนะนำเฉพาะบุคคล" in agent.description


@patch("agents.personalization.agent.date")
def test_personalization_agent_run_returns_structured_output(mock_date):
    """Agent should return recommendations that respect configuration"""

    _set_fixed_today(mock_date)
    agent = PersonalizationAgent()
    input_payload = _build_sample_request()

    result = agent.run(input_payload)

    assert isinstance(result.personalized_recommendation, list)
    assert len(result.personalized_recommendation) == 1

    recommendation_block = result.personalized_recommendation[0]
    assert isinstance(recommendation_block, PersonalizedRecommendation)
    assert recommendation_block.recommend_to == "U001"
    assert len(recommendation_block.recommendation) == 3

    # First item should be the highest priority video, and not recently completed
    first_item = recommendation_block.recommendation[0]
    assert first_item.type == "video"
    assert first_item.video_id != "V05"
    assert first_item.confidence_pct >= 70

    # All priorities must be sequential starting from 1
    priorities = [item.priority for item in recommendation_block.recommendation]
    assert priorities == [1, 2, 3]

    # Action plan should have entries for each recommendation type
    assert len(recommendation_block.action_plan) >= 2
    assert recommendation_block.meta.recommend_top_n == 3
    assert recommendation_block.meta.self_check.all_sections_present is True
    assert recommendation_block.meta.self_check.no_empty_fields is True
    assert recommendation_block.alert == []


@patch("agents.personalization.agent.date")
def test_personalization_agent_flags_low_confidence_and_engagement(mock_date):
    """Low retention and engagement should trigger alerts"""

    _set_fixed_today(mock_date)
    today = FIXED_TODAY
    request = PersonalizationRequest(
        user_id="U002",
        profile=UserProfile(
            age=32,
            gender="female",
            location="Chiang Mai",
            interest=["สุขภาพจิต"],
        ),
        view_history=[
            ViewHistoryItem(
                video_id="X01",
                title="คลายกังวล",
                watched_pct=25,
                date=today - timedelta(days=2),
            ),
            ViewHistoryItem(
                video_id="X02",
                title="ยืดเหยียดผ่อนคลาย",
                watched_pct=30,
                date=today - timedelta(days=5),
            ),
        ],
        engagement=EngagementMetrics(like=0, comment=0, share=0),
        trend=[TrendInterest(topic="สุขภาพจิต", score=40)],
        config=PersonalizationConfig(recommend_top_n=2, min_confidence_pct=80),
    )
    agent = PersonalizationAgent()
    result = agent.run(PersonalizationInput(personalization_request=request))
    alerts = result.personalized_recommendation[0].alert

    assert any("ความมั่นใจ" in alert for alert in alerts)
    assert any("retention ต่ำกว่า 40%" in alert for alert in alerts)
    assert any("engagement ต่ำ" in alert for alert in alerts)
