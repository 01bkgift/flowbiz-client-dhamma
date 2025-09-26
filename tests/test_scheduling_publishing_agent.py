"""Tests for SchedulingPublishingAgent."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from agents import (
    AudienceAnalytics,
    ContentCalendarEntry,
    ScheduleConstraints,
    SchedulingInput,
    SchedulingOutput,
    SchedulingPublishingAgent,
)


@pytest.fixture
def basic_input() -> SchedulingInput:
    return SchedulingInput(
        content_calendar=[
            ContentCalendarEntry(
                video_id="V01",
                topic_title="ปล่อยวางความกังวลก่อนนอน",
                priority_score=92.5,
                pillar="ธรรมะประยุกต์",
                content_type="longform",
                expected_duration_min=12,
                suggested_publish_week="W1",
                ready_to_publish=True,
            ),
            ContentCalendarEntry(
                video_id="V02",
                topic_title="ธรรมะสั้นช่วงเช้า",
                priority_score=88.0,
                pillar="ธรรมะประยุกต์",
                content_type="longform",
                expected_duration_min=8,
                suggested_publish_week="W1",
                ready_to_publish=True,
            ),
            ContentCalendarEntry(
                video_id="V03",
                topic_title="Q&A การภาวนาครอบครัว",
                priority_score=81.0,
                pillar="Q&A/ตอบคำถาม",
                content_type="shorts",
                expected_duration_min=5,
                suggested_publish_week="W1",
                ready_to_publish=True,
            ),
            ContentCalendarEntry(
                video_id="V04",
                topic_title="รวมคลิปสรุปสัปดาห์",
                priority_score=60.0,
                pillar="ชาดก/นิทานสอนใจ",
                content_type="longform",
                expected_duration_min=15,
                suggested_publish_week="W1",
                ready_to_publish=False,
            ),
        ],
        constraints=ScheduleConstraints(
            max_videos_per_day=2,
            max_longform_per_week=4,
            max_shorts_per_week=6,
            avoid_duplicate_pillar_in_24hr=True,
            forbidden_times=[],
            planning_start_date=date(2025, 10, 6),
        ),
        audience_analytics=AudienceAnalytics(
            top_time_slots_utc=["20:00", "18:00", "21:30"],
            lowest_traffic_slots_utc=["02:00", "03:00"],
            recent_best_days=["Friday", "Sunday", "Monday"],
            timezone="Asia/Bangkok",
        ),
    )


def test_scheduling_agent_assigns_slots(basic_input: SchedulingInput) -> None:
    agent = SchedulingPublishingAgent()
    result = agent.run(basic_input)

    assert isinstance(result, SchedulingOutput)
    assert len(result.schedule_plan) == 4
    assert not result.warnings

    by_id = {item.video_id: item for item in result.schedule_plan}

    v01 = by_id["V01"]
    assert v01.publish_status == "scheduled"
    assert v01.scheduled_datetime_local is not None
    assert v01.scheduled_datetime_local.strftime("%Y-%m-%d %H:%M") == "2025-10-06 20:00"

    v02 = by_id["V02"]
    assert v02.publish_status == "scheduled"
    assert v02.scheduled_datetime_local is not None
    assert v02.scheduled_datetime_local > v01.scheduled_datetime_local
    assert v02.scheduled_datetime_local - v01.scheduled_datetime_local >= timedelta(
        hours=24
    )

    v03 = by_id["V03"]
    assert v03.publish_status == "scheduled"
    assert v03.scheduled_datetime_local is not None
    assert v03.scheduled_datetime_local.weekday() in {0, 4, 6}

    v04 = by_id["V04"]
    assert v04.publish_status == "pending"
    assert v04.scheduled_datetime_local is None

    assert result.meta.total_videos == 4
    assert result.meta.scheduled_count == 3
    assert result.meta.pending_count == 1
    assert result.meta.collision_count == 0
    assert result.meta.overflow_count == 0
    assert result.meta.self_check.no_collision is True
    assert result.meta.self_check.no_overflow is True
    assert result.meta.self_check.all_ready_have_slot is True


def test_scheduling_agent_collision_and_overflow() -> None:
    # Forbidden intervals allow only Monday 20:00 for two weeks
    forbidden = [
        "2025-10-06T00:00:00Z/2025-10-06T13:00:00Z",
        "2025-10-06T13:01:00Z/2025-10-07T00:00:00Z",
        "2025-10-07T00:00:00Z/2025-10-13T00:00:00Z",
        "2025-10-13T00:00:00Z/2025-10-20T00:00:00Z",
        "2025-10-20T00:00:00Z/2025-10-27T00:00:00Z",
        "2025-10-27T00:00:00Z/2025-11-03T00:00:00Z",
        "2025-11-03T00:00:00Z/2025-11-10T00:00:00Z",
        "2025-11-10T00:00:00Z/2025-11-17T00:00:00Z",
        "2025-11-17T00:00:00Z/2025-11-24T00:00:00Z",
        "2025-11-24T00:00:00Z/2025-12-01T00:00:00Z",
    ]

    input_data = SchedulingInput(
        content_calendar=[
            ContentCalendarEntry(
                video_id="A",
                topic_title="ธรรมะเย็นใจ",
                priority_score=90.0,
                pillar="ธรรมะประยุกต์",
                content_type="longform",
                suggested_publish_week="W1",
                ready_to_publish=True,
            ),
            ContentCalendarEntry(
                video_id="B",
                topic_title="ภาวนาสำหรับมือใหม่",
                priority_score=85.0,
                pillar="ธรรมะประยุกต์",
                content_type="longform",
                suggested_publish_week="W1",
                ready_to_publish=True,
            ),
            ContentCalendarEntry(
                video_id="C",
                topic_title="ชวนสวดมนต์",
                priority_score=70.0,
                pillar="ธรรมะประยุกต์",
                content_type="longform",
                suggested_publish_week="W1",
                ready_to_publish=True,
            ),
        ],
        constraints=ScheduleConstraints(
            max_videos_per_day=2,
            max_longform_per_week=3,
            max_shorts_per_week=5,
            avoid_duplicate_pillar_in_24hr=True,
            forbidden_times=forbidden,
            planning_start_date=date(2025, 10, 6),
        ),
        audience_analytics=AudienceAnalytics(
            top_time_slots_utc=["20:00"],
            lowest_traffic_slots_utc=["19:00"],
            recent_best_days=["Monday"],
            timezone="Asia/Bangkok",
        ),
    )

    agent = SchedulingPublishingAgent()
    result = agent.run(input_data)

    by_id = {item.video_id: item for item in result.schedule_plan}

    assert by_id["A"].publish_status == "scheduled"
    assert by_id["B"].publish_status == "collision"
    assert by_id["B"].collision_with == "A"
    assert by_id["C"].publish_status == "overflow"

    assert result.meta.collision_count == 1
    assert result.meta.overflow_count == 1
    assert result.meta.self_check.no_collision is False
    assert result.meta.self_check.no_overflow is False
    assert result.warnings  # warnings should include collision/overflow notes


def test_agent_requires_anchor_for_base_week(basic_input: SchedulingInput) -> None:
    agent = SchedulingPublishingAgent()

    anchorless_input = basic_input.model_copy(
        update={
            "constraints": ScheduleConstraints(
                max_videos_per_day=basic_input.constraints.max_videos_per_day,
                max_longform_per_week=basic_input.constraints.max_longform_per_week,
                max_shorts_per_week=basic_input.constraints.max_shorts_per_week,
                avoid_duplicate_pillar_in_24hr=basic_input.constraints.avoid_duplicate_pillar_in_24hr,
                forbidden_times=[],
            )
        }
    )

    with pytest.raises(ValueError):
        agent.run(anchorless_input)
