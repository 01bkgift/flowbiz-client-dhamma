"""Tests for the MultiChannelPublishAgent."""

from datetime import datetime

from agents.multi_channel_publish import (
    MultiChannelPublishAgent,
    MultiChannelPublishInput,
    PublishAssets,
    PublishRequest,
)


def _build_input(**overrides):
    base_request = PublishRequest(
        content_id="V01",
        title="ปล่อยวางความกังวลก่อนนอน",
        description="คลิปธรรมะดีดี...",
        tags=["ธรรมะ", "นอนหลับ", "ปล่อยวาง"],
        schedule={
            "YouTube": "2025-10-06T20:00:00+07:00",
            "TikTok": "2025-10-07T09:00:00+07:00",
            "Facebook": "2025-10-07T09:30:00+07:00",
        },
        privacy={
            "YouTube": "public",
            "TikTok": "public",
            "Facebook": "public",
        },
        assets=PublishAssets(
            video="V01.mp4",
            vertical_video="V01_tiktok.mp4",
            thumbnail="V01_thumb.jpg",
        ),
        channels=["YouTube", "TikTok", "Facebook"],
        extra_setting={
            "TikTok": {
                "caption": "เคล็ดลับปล่อยวางก่อนนอน",
                "hashtag": ["#ธรรมะดีดี", "#นอนหลับสบาย"],
            },
            "Facebook": {
                "post_message": "ฟังธรรมะก่อนนอนเพื่อใจสงบ",
            },
        },
    )
    return MultiChannelPublishInput(
        publish_request=base_request.model_copy(update=overrides)
    )


def test_agent_returns_ready_payload_for_complete_request():
    agent = MultiChannelPublishAgent()
    result = agent.run(_build_input())

    assert len(result.multi_channel_publish_payload) == 3
    assert all(
        payload.status == "ready" for payload in result.multi_channel_publish_payload
    )
    assert not result.warnings
    assert not result.errors
    assert all(
        log.event == "mapping_success" and log.status == "success"
        for log in result.multi_channel_publish_log
    )
    # Ensure timestamps are datetime and close to now
    assert all(
        isinstance(log.timestamp, datetime) for log in result.multi_channel_publish_log
    )


def test_agent_flags_missing_vertical_video_for_tiktok():
    agent = MultiChannelPublishAgent()
    input_data = _build_input(
        assets=PublishAssets(
            video="V01.mp4",
            vertical_video=None,
            thumbnail="V01_thumb.jpg",
        )
    )
    result = agent.run(input_data)

    tiktok_payload = next(
        payload
        for payload in result.multi_channel_publish_payload
        if payload.channel == "TikTok"
    )
    assert tiktok_payload.status == "missing_data"
    assert "เตรียมไฟล์วิดีโอแนวตั้งสำหรับ TikTok" in tiktok_payload.suggestion
    assert any(
        "TikTok payload missing fields" in warning for warning in result.warnings
    )
    assert any(log.status == "warning" for log in result.multi_channel_publish_log)


def test_agent_marks_unknown_channel_as_error():
    agent = MultiChannelPublishAgent()
    input_data = MultiChannelPublishInput(
        publish_request=PublishRequest(
            content_id="X1",
            title="Test",
            description="Desc",
            tags=[],
            schedule={},
            privacy={},
            assets=PublishAssets(),
            channels=["YouTube", "MySpace"],
            extra_setting={},
        )
    )
    result = agent.run(input_data)

    error_payload = next(
        payload
        for payload in result.multi_channel_publish_payload
        if payload.channel == "MySpace"
    )
    assert error_payload.status == "error"
    assert result.errors
    assert any(
        log.channel == "MySpace" and log.status == "failed"
        for log in result.multi_channel_publish_log
    )
