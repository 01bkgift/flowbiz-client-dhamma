"""Tests for SeoMetadataAgent."""

import sys
from pathlib import Path

import pytest

# Ensure src is on path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agents.seo_metadata import SeoMetadataAgent, SeoMetadataInput  # noqa: E402


@pytest.fixture
def seo_input() -> SeoMetadataInput:
    return SeoMetadataInput(
        topic_title="ปล่อยวางความกังวลก่อนนอน",
        script_summary=(
            "คลิปนี้แนะนำวิธีปล่อยวางความกังวลก่อนนอน ด้วยการสังเกตกายใจ "
            "หายใจลึก และใช้หลักธรรมะเพื่อคืนสู่ความสงบ"
        ),
        citations_list=[
            "พุทธวจนะ: 'รู้ตัวทันทีเมื่อใจเครียด' (SN 36.1)",
            "หลักอานาปานสติ (MN 118)",
        ],
        primary_keywords=["ปล่อยวาง", "นอนหลับ", "ใจสงบ", "ธรรมะ", "สติ"],
    )


def test_generate_metadata_structure(seo_input: SeoMetadataInput) -> None:
    agent = SeoMetadataAgent()
    result = agent.run(seo_input)

    assert result.title.startswith(seo_input.primary_keywords[0])
    assert len(result.title) <= 60
    assert "Key Teachings:" in result.description
    assert "Citations:" in result.description
    assert result.tags[0] == seo_input.primary_keywords[0]
    assert 15 <= len(result.tags) <= 25
    assert all(tag for tag in result.tags)

    first_paragraph = result.description.split("\n\n")[0]
    assert len(first_paragraph) <= 200

    hashtag_line = result.description.strip().split("\n")[-1]
    assert hashtag_line.startswith("#")
    assert result.meta.title_length == len(result.title)
    assert result.meta.description_length == len(result.description)
    assert result.meta.tags_count == len(result.tags)
    assert result.meta.hashtags_count <= 8
    assert result.meta.primary_keyword_in_title is True
    assert result.meta.no_clickbait is True
    assert result.meta.self_check.title_within_60 is True
    assert result.meta.self_check.description_within_400 is True
    assert result.meta.self_check.tags_15_25 is True
    assert result.meta.self_check.hashtags_le_8 is True
    assert result.warnings == []


def test_generate_metadata_truncates_summary() -> None:
    long_summary = "การรู้สึกตัว" * 100
    agent = SeoMetadataAgent()
    input_data = SeoMetadataInput(
        topic_title="ฝึกสติก่อนนอน",
        script_summary=long_summary,
        citations_list=[],
        primary_keywords=["สติ", "ผ่อนคลาย"],
    )

    result = agent.run(input_data)

    first_paragraph = result.description.split("\n\n")[0]
    assert len(first_paragraph) <= 200
    assert "…" in first_paragraph
    assert "ไม่มีการอ้างอิงเพิ่มเติม" in result.description
    assert "ควรเพิ่ม Hashtags" not in result.warnings  # hashtags auto-added
    assert any("ไม่มีการอ้างอิง" in warn for warn in result.warnings)
