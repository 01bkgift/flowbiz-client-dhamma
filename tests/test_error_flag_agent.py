"""Tests for the ErrorFlagAgent."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agents.error_flag import ErrorFlagAgent, ErrorFlagInput


def build_agent_logs() -> ErrorFlagInput:
    return ErrorFlagInput(
        agent_logs=[
            {
                "agent": "Analytics & Retention Agent",
                "error": None,
                "flags": ["mid_clip_drop", "low_comments"],
                "warnings": [],
            },
            {
                "agent": "Scheduling & Publishing Agent",
                "error": {
                    "code": "OVERLAP",
                    "message": "พบวิดีโอ pillar ซ้ำใน 24 ชม.",
                    "suggested_fix": "เลื่อน publish slot วิดีโอหนึ่งไปวันถัดไป",
                },
                "flags": [],
                "warnings": ["overflow_count > 0"],
            },
        ]
    )


def test_error_flag_agent_produces_expected_summary() -> None:
    agent = ErrorFlagAgent()
    input_payload = build_agent_logs()

    result = agent.run(input_payload)

    assert result.summary == [
        "Scheduling & Publishing Agent พบวิดีโอ pillar ซ้ำใน 24 ชม. (OVERLAP)",
        "Analytics & Retention Agent flag mid_clip_drop, low_comments",
    ]

    assert result.critical[0].model_dump() == {
        "agent": "Scheduling & Publishing Agent",
        "error_code": "OVERLAP",
        "message": "พบวิดีโอ pillar ซ้ำใน 24 ชม.",
        "suggested_action": "เลื่อน publish slot วิดีโอหนึ่งไปวันถัดไป",
    }

    warning_payloads = [item.model_dump() for item in result.warning]
    assert warning_payloads == [
        {
            "agent": "Analytics & Retention Agent",
            "flag": "mid_clip_drop",
            "warning": None,
            "message": "Retention ลดช่วงกลางคลิป",
            "suggested_action": "ปรับ pacing, shorten ช่วงกลาง",
        },
        {
            "agent": "Analytics & Retention Agent",
            "flag": "low_comments",
            "warning": None,
            "message": "จำนวนคอมเมนต์ต่ำกว่าค่าเฉลี่ย",
            "suggested_action": "เพิ่ม CTA กระตุ้นคอมเมนต์",
        },
        {
            "agent": "Scheduling & Publishing Agent",
            "flag": None,
            "warning": "overflow_count > 0",
            "message": "มีวิดีโอรอ publish เกินโควต้าต่อวัน/สัปดาห์",
            "suggested_action": "กระจาย schedule เพิ่มหรือเพิ่ม slot",
        },
    ]

    assert result.root_cause == ["ยังไม่พบ recurring error/flag จากข้อมูลรอบนี้"]

    assert result.meta.model_dump() == {
        "total_error": 1,
        "total_flag": 2,
        "total_warning": 1,
        "unique_agents": 2,
        "self_check": {
            "all_sections_present": True,
            "no_empty_fields": True,
        },
    }


def test_error_flag_agent_detects_recurring_root_causes() -> None:
    agent = ErrorFlagAgent()
    payload = ErrorFlagInput(
        agent_logs=[
            {
                "agent": "Analytics & Retention Agent",
                "error": None,
                "flags": ["mid_clip_drop"],
                "warnings": [],
            },
            {
                "agent": "Feedback Agent",
                "error": None,
                "flags": ["mid_clip_drop"],
                "warnings": [],
            },
            {
                "agent": "Scheduling & Publishing Agent",
                "error": {
                    "code": "OVERLAP",
                    "message": "พบวิดีโอ pillar ซ้ำใน 24 ชม.",
                    "suggested_fix": "เลื่อน publish slot วิดีโอหนึ่งไปวันถัดไป",
                },
                "flags": ["OVERLAP"],
                "warnings": ["overflow_count > 0", "overflow_count > 0"],
            },
            {
                "agent": "Scheduling & Publishing Agent",
                "error": {
                    "code": "OVERLAP",
                    "message": "พบวิดีโอ pillar ซ้ำใน 24 ชม.",
                    "suggested_fix": "เลื่อน publish slot วิดีโอหนึ่งไปวันถัดไป",
                },
                "flags": [],
                "warnings": [],
            },
        ]
    )

    result = agent.run(payload)

    assert sorted(result.root_cause) == sorted(
        [
            "พบวิดีโอ pillar ซ้ำใน 24 ชม. พบ 2 ครั้ง",
            "Flag 'mid_clip_drop' (Retention ลดช่วงกลางคลิป) เกิดขึ้น 2 ครั้ง",
            "Warning 'overflow_count > 0' (มีวิดีโอรอ publish เกินโควต้าต่อวัน/สัปดาห์) เกิดขึ้น 2 ครั้ง",
        ]
    )

    assert result.meta.total_flag == 3
    assert result.meta.total_warning == 2
    assert result.meta.total_error == 2
