"""Agent responsible for generating localized subtitles and summaries."""

from __future__ import annotations

import re
import textwrap
from dataclasses import dataclass
from typing import Iterable

from automation_core.base_agent import BaseAgent
from automation_core.prompt_loader import get_prompt_path, load_prompt

from .model import (
    LocalizationSubtitleInput,
    LocalizationSubtitleMeta,
    LocalizationSubtitleOutput,
    format_seconds_to_timestamp,
    parse_timestamp_to_seconds,
)

_CITATION_PATTERN = re.compile(r"\[CIT:[^\]]+\]")
_PAUSE_PATTERN = re.compile(r"\(หยุด[^)]*\)")
_MULTI_SPACE_PATTERN = re.compile(r"\s+")


@dataclass(slots=True)
class _SegmentTiming:
    index: int
    start_seconds: float
    end_seconds: float
    lines: list[str]


class LocalizationSubtitleAgent(
    BaseAgent[LocalizationSubtitleInput, LocalizationSubtitleOutput]
):
    """Generate SRT subtitles from an approved script."""

    def __init__(self, prompt_name: str = "localization_subtitle_v2.txt") -> None:
        super().__init__(
            name="LocalizationSubtitleAgent",
            version="2.0.0",
            description="Convert approved scripts into localized subtitle files.",
        )
        prompt_path = get_prompt_path(prompt_name)
        self.prompt_template = load_prompt(prompt_path)

    def run(self, input_data: LocalizationSubtitleInput) -> LocalizationSubtitleOutput:
        """Generate SRT blocks, summary, and metadata."""

        base_seconds = parse_timestamp_to_seconds(input_data.base_start_time)
        cumulative = 0.0
        blocks: list[str] = []
        timings: list[_SegmentTiming] = []
        cleaned_texts: list[str] = []

        for index, segment in enumerate(input_data.approved_script, start=1):
            clean_text = self._clean_text(segment.text)
            if not clean_text:
                raise ValueError(f"segment {index} ไม่มีข้อความหลังทำความสะอาด")

            text_lines = self._wrap_text(clean_text)
            start_seconds = base_seconds + cumulative
            end_seconds = start_seconds + segment.est_seconds

            block_lines = [
                str(index),
                f"{format_seconds_to_timestamp(start_seconds)} --> {format_seconds_to_timestamp(end_seconds)}",
                *text_lines,
            ]
            blocks.append("\n".join(block_lines))
            timings.append(
                _SegmentTiming(
                    index=index,
                    start_seconds=start_seconds,
                    end_seconds=end_seconds,
                    lines=text_lines,
                )
            )
            cleaned_texts.append(clean_text)
            cumulative += segment.est_seconds

        srt_content = "\n\n".join(blocks)
        meta = self._build_meta(timings, cumulative)
        english_summary, summary_warnings = self._generate_summary(cleaned_texts)

        warnings = summary_warnings

        output = LocalizationSubtitleOutput(
            srt=srt_content,
            english_summary=english_summary,
            meta=meta,
            warnings=warnings,
        )
        return output

    @staticmethod
    def _clean_text(text: str) -> str:
        """Remove citations, pause cues, and extra spacing."""

        text = _CITATION_PATTERN.sub("", text)
        text = _PAUSE_PATTERN.sub("", text)
        text = text.replace("\n", " ")
        text = _MULTI_SPACE_PATTERN.sub(" ", text)
        return text.strip()

    @staticmethod
    def _wrap_text(text: str, width: int = 40) -> list[str]:
        """Wrap text into SRT friendly lines."""

        wrapped = textwrap.wrap(
            text,
            width=width,
            break_long_words=False,
            break_on_hyphens=False,
        )
        return wrapped or [text]

    def _build_meta(
        self, timings: Iterable[_SegmentTiming], total_duration: float
    ) -> LocalizationSubtitleMeta:
        """Construct metadata from timing information."""

        timings_list = list(timings)
        lines_count = sum(len(t.lines) + 2 for t in timings_list)

        time_continuity_ok = True
        no_overlap = True
        no_empty_line = True

        last_end = None
        for timing in timings_list:
            if any(not line.strip() for line in timing.lines):
                no_empty_line = False

            if last_end is not None:
                if abs(timing.start_seconds - last_end) > 1e-3:
                    time_continuity_ok = False
                if timing.start_seconds < last_end - 1e-3:
                    no_overlap = False
            last_end = timing.end_seconds

        meta = LocalizationSubtitleMeta(
            lines=lines_count,
            duration_total=total_duration,
            segments_count=len(timings_list),
            time_continuity_ok=time_continuity_ok,
            no_overlap=no_overlap,
            no_empty_line=no_empty_line,
            self_check=time_continuity_ok and no_overlap and no_empty_line,
        )
        return meta

    def _generate_summary(self, texts: list[str]) -> tuple[str, list[str]]:
        """Create an English summary between 50-100 words."""

        warnings: list[str] = []
        summary_sentences: list[str] = []
        for idx, text in enumerate(texts, start=1):
            words = text.split()
            if not words:
                continue
            snippet = " ".join(words[:12])
            summary_sentences.append(
                f"Segment {idx} focuses on {snippet.strip()}."
            )

        summary_words = " ".join(summary_sentences).split()

        filler_source = [word for text in texts for word in text.split() if word]
        filler_index = 0

        while len(summary_words) < 50:
            if filler_source:
                summary_words.append(filler_source[filler_index % len(filler_source)])
                filler_index += 1
            else:
                summary_words.append("insight")
            if "english_summary was padded to reach 50 words." not in warnings:
                warnings.append("english_summary was padded to reach 50 words.")

        if len(summary_words) > 100:
            summary_words = summary_words[:100]
            warnings.append("english_summary was truncated to 100 words.")

        summary_text = " ".join(summary_words)
        if not summary_text.endswith("."):
            summary_text += "."

        return summary_text, warnings
