"""Tests for the localization subtitle agent."""

import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agents.localization_subtitle import (  # noqa: E402  pylint: disable=wrong-import-position
    LocalizationSubtitleAgent,
    LocalizationSubtitleInput,
    LocalizationSubtitleMeta,
    LocalizationSubtitleOutput,
    SubtitleSegment,
)


class TestLocalizationSubtitleAgent:
    """Test suite for subtitle generation."""

    def test_generate_subtitles_success(self):
        agent = LocalizationSubtitleAgent()
        input_data = LocalizationSubtitleInput(
            base_start_time="00:00:05,000",
            approved_script=[
                SubtitleSegment(
                    segment_type="intro",
                    text="""
                    Welcome friends to this calm breathing journey that gently invites
                    awareness to every inhale and exhale while softening the body and
                    centering the wandering thoughts. [CIT:ABC001] (หยุด 2 วิ)
                    """,
                    est_seconds=8,
                ),
                SubtitleSegment(
                    segment_type="teaching",
                    text="""
                    In this section we explore compassionate attention, noticing how
                    tension rises and dissolves with kindness and patience so the heart
                    can rest in the present moment without judgment. [CIT:ABC002]
                    """,
                    est_seconds=10,
                ),
                SubtitleSegment(
                    segment_type="practice",
                    text="""
                    Continue breathing deeply, silently repeating the mantra of peace
                    and clarity as you observe sensations, sounds, and feelings moving
                    through experience like gentle clouds across the sky. (หยุด สั้น)
                    """,
                    est_seconds=9,
                ),
                SubtitleSegment(
                    segment_type="closing",
                    text="""
                    As we close, offer gratitude to yourself and to everyone walking
                    this path, carrying a light of mindfulness into daily actions and
                    relationships with sincerity, warmth, and hopeful courage.
                    """,
                    est_seconds=11,
                ),
            ],
        )

        output = agent.run(input_data)

        # Validate SRT structure
        blocks = [
            block.strip() for block in output.srt.strip().split("\n\n") if block.strip()
        ]
        assert len(blocks) == 4
        for idx, block in enumerate(blocks, start=1):
            lines = block.splitlines()
            assert lines[0].strip() == str(idx)
            assert "[CIT:" not in block
            assert "(หยุด" not in block

        # Validate meta information
        assert output.meta.segments_count == 4
        assert output.meta.duration_total == pytest.approx(38.0)
        assert output.meta.time_continuity_ok is True
        assert output.meta.no_overlap is True
        assert output.meta.no_empty_line is True
        assert output.meta.self_check is True

        # Summary should respect length requirements
        summary_words = [
            w for w in re.split(r"\s+", output.english_summary.strip()) if w
        ]
        assert 50 <= len(summary_words) <= 100
        assert output.warnings == []

    def test_empty_segment_after_cleaning_raises(self):
        agent = LocalizationSubtitleAgent()
        input_data = LocalizationSubtitleInput(
            base_start_time="00:00:00,000",
            approved_script=[
                SubtitleSegment(
                    segment_type="invalid",
                    text="[CIT:ONLY] (หยุด 1 วิ)",
                    est_seconds=5,
                )
            ],
        )

        with pytest.raises(ValueError, match="ไม่มีข้อความหลังทำความสะอาด"):
            agent.run(input_data)


class TestLocalizationSubtitleModelValidation:
    """Unit tests for the underlying Pydantic models."""

    def test_input_invalid_timestamp(self):
        with pytest.raises(ValueError, match="รูปแบบ HH:MM:SS,mmm"):
            LocalizationSubtitleInput(
                base_start_time="5:00",
                approved_script=[
                    SubtitleSegment(
                        segment_type="intro",
                        text="Valid text",
                        est_seconds=5,
                    )
                ],
            )

    def test_output_summary_length_validation(self):
        meta = LocalizationSubtitleMeta(
            lines=3,
            duration_total=5.0,
            segments_count=1,
            time_continuity_ok=True,
            no_overlap=True,
            no_empty_line=True,
            self_check=True,
        )
        srt = "1\n00:00:00,000 --> 00:00:05,000\nA mindful breath."

        with pytest.raises(ValueError, match="50-100 คำ"):
            LocalizationSubtitleOutput(
                srt=srt,
                english_summary="Too short",
                meta=meta,
            )

    def test_output_timestamp_validation(self):
        meta = LocalizationSubtitleMeta(
            lines=3,
            duration_total=0.0,
            segments_count=1,
            time_continuity_ok=True,
            no_overlap=True,
            no_empty_line=True,
            self_check=True,
        )
        srt = "1\n00:00:00,000 --> 00:00:00,000\nText line"

        with pytest.raises(ValueError, match="เวลาเริ่มต้องน้อยกว่าเวลาสิ้นสุด"):
            LocalizationSubtitleOutput(
                srt=srt,
                english_summary=" ".join(["word"] * 50),
                meta=meta,
            )
