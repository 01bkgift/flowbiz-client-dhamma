"""SEO Metadata generation agent."""

from __future__ import annotations

import logging
import re
from collections.abc import Iterable

from automation_core.base_agent import BaseAgent

from .model import (
    MetaInfo,
    SelfCheck,
    SeoMetadataInput,
    SeoMetadataOutput,
)

logger = logging.getLogger(__name__)


class SeoMetadataAgent(BaseAgent[SeoMetadataInput, SeoMetadataOutput]):
    """Generate SEO friendly metadata for Dhamma Dee Dee YouTube videos."""

    def __init__(self) -> None:
        super().__init__(
            name="SeoMetadataAgent",
            version="1.0.0",
            description="สร้าง SEO metadata สำหรับวิดีโอช่องธรรมะดีดี",
        )

        self._clickbait_keywords = {
            "การันตี",
            "100%",
            "ด่วน",
            "พลาดไม่ได้",
            "ช็อก",
            "มหัศจรรย์",
            "ฟรี",
            "รวยทันที",
        }

        self._generic_tags = [
            "ธรรมะ",
            "สติ",
            "สมาธิ",
            "ธรรมะดีดี",
            "ผ่อนคลาย",
            "คลายเครียด",
            "สุขภาพจิต",
            "ฝึกสมาธิ",
            "ปฏิบัติธรรม",
            "บำรุงใจ",
            "mindfulness",
            "meditation",
            "buddhist",
            "calm",
            "sleep",
            "relax",
            "stress relief",
            "mental health",
            "peace",
            "night routine",
            "breathing",
            "self care",
        ]

    def run(self, input_data: SeoMetadataInput) -> SeoMetadataOutput:
        logger.info("สร้าง SEO metadata สำหรับหัวข้อ: %s", input_data.topic_title)

        primary_keyword = input_data.primary_keywords[0]
        title = self._generate_title(input_data.topic_title, primary_keyword)
        tags = self._generate_tags(input_data, primary_keyword)
        hashtags = self._generate_hashtags(input_data, primary_keyword)
        description = self._generate_description(
            input_data.script_summary,
            input_data.citations_list,
            tags,
            hashtags,
            primary_keyword,
            input_data.topic_title,
        )

        title_length = len(title)
        description_length = len(description)
        hashtags_count = len(hashtags)
        tags_count = len(tags)
        first_paragraph_length = len(description.split("\n\n")[0])

        primary_keyword_in_title = title.startswith(primary_keyword)
        no_clickbait = self._check_no_clickbait(title, description)

        self_check = SelfCheck(
            title_within_60=title_length <= 60,
            description_within_400=first_paragraph_length <= 400,
            tags_15_25=15 <= tags_count <= 25,
            hashtags_le_8=hashtags_count <= 8,
        )

        warnings: list[str] = []
        if first_paragraph_length > 200:
            warnings.append(
                "ย่อหน้าแรกของคำอธิบายยาวเกิน 200 ตัวอักษร ควรปรับให้กระชับ"
            )
        if not primary_keyword_in_title:
            warnings.append("หัวข้อไม่ได้ขึ้นต้นด้วยคีย์เวิร์ดหลัก")
        if not no_clickbait:
            warnings.append("พบคำที่อาจตีความเป็น clickbait")
        if hashtags_count == 0:
            warnings.append("ควรเพิ่ม Hashtags ในคำอธิบาย")
        if not input_data.citations_list:
            warnings.append("ไม่มีการอ้างอิงในส่วน Citations")

        meta = MetaInfo(
            title_length=title_length,
            description_length=description_length,
            tags_count=tags_count,
            hashtags_count=hashtags_count,
            primary_keyword_in_title=primary_keyword_in_title,
            no_clickbait=no_clickbait,
            self_check=self_check,
        )

        result = SeoMetadataOutput(
            title=title,
            description=description,
            tags=tags,
            meta=meta,
            warnings=warnings,
        )

        logger.info("สร้าง SEO metadata สำเร็จ (title length=%s)", title_length)
        return result

    def _generate_title(self, topic_title: str, primary_keyword: str) -> str:
        base_title = topic_title.strip()
        keyword = primary_keyword.strip()

        if keyword and not base_title.startswith(keyword):
            if base_title.lower().startswith(keyword.lower()):
                base_title = f"{keyword}{base_title[len(keyword):]}"
            else:
                base_title = f"{keyword} {base_title}".strip()

        base_title = re.sub(r"\s+", " ", base_title)
        if len(base_title) <= 60:
            return base_title

        words = base_title.split()
        trimmed_words: list[str] = []
        for word in words:
            candidate = " ".join(trimmed_words + [word]) if trimmed_words else word
            if len(candidate) <= 60:
                trimmed_words.append(word)
            else:
                break

        if not trimmed_words:
            return base_title[:60]

        return " ".join(trimmed_words)

    def _generate_description(
        self,
        script_summary: str,
        citations: list[str],
        tags: list[str],
        hashtags: list[str],
        primary_keyword: str,
        topic_title: str,
    ) -> str:
        first_paragraph = self._truncate_text(script_summary.strip(), 200)

        key_teachings = self._build_key_teachings(
            script_summary, primary_keyword, topic_title
        )
        if not citations:
            citation_lines = ["- ไม่มีการอ้างอิงเพิ่มเติม"]
        else:
            citation_lines = [f"- {citation}" for citation in citations[:3]]

        description_lines = [first_paragraph, "", "Key Teachings:"]
        description_lines.extend(f"- {teaching}" for teaching in key_teachings)
        description_lines.extend(["", "Citations:"])
        description_lines.extend(citation_lines)

        hashtag_line = " ".join(hashtags)
        if hashtag_line:
            description_lines.extend(["", hashtag_line])

        return "\n".join(description_lines)

    def _build_key_teachings(
        self, script_summary: str, primary_keyword: str, topic_title: str
    ) -> list[str]:
        cleaned_summary = script_summary.strip().rstrip("。").rstrip(".")
        cleaned_summary = cleaned_summary.replace("คลิปนี้", "เนื้อหานี้")

        segments = re.split(r"ด้วยการ|พร้อม|และ|,|;|โดยการ", cleaned_summary)
        candidates = [
            segment.strip(" .")
            for segment in segments
            if segment.strip() and len(segment.strip()) > 4
        ]

        teachings: list[str] = []
        for segment in candidates:
            phrase = segment
            if not phrase.startswith("การ") and not phrase.startswith("ฝึก"):
                phrase = f"การ{phrase}" if len(phrase) < 40 else phrase
            phrase = phrase.replace("  ", " ")
            teachings.append(phrase)
            if len(teachings) >= 3:
                break

        if not teachings:
            teachings.append(
                f"การประยุกต์{primary_keyword or topic_title}ให้ใจสงบ"
            )

        if len(teachings) == 1:
            teachings.append("ฝึกสติเพื่อรู้เท่าทันความคิดก่อนพักผ่อน")
        if len(teachings) == 2:
            teachings.append("ย้ำหลักเมตตาและการยอมรับตนเองก่อนเข้านอน")

        return teachings[:5]

    def _generate_tags(
        self, input_data: SeoMetadataInput, primary_keyword: str
    ) -> list[str]:
        tags: list[str] = []

        def add_unique(values: Iterable[str]) -> None:
            for value in values:
                cleaned = value.strip()
                if not cleaned:
                    continue
                if cleaned not in tags:
                    tags.append(cleaned)

        add_unique(input_data.primary_keywords)

        topic_terms = re.split(r"\s+", input_data.topic_title)
        for term in topic_terms:
            if term and len(term) > 1:
                add_unique([term])

        if primary_keyword:
            add_unique([f"{primary_keyword}ก่อนนอน", f"ฝึก{primary_keyword}"])

        summary_keywords = re.findall(r"[\u0E00-\u0E7Fa-zA-Z]+", input_data.script_summary)
        add_unique(summary_keywords[:5])

        add_unique(self._generic_tags)

        if len(tags) < 15:
            add_unique(
                [
                    "ปล่อยวาง",
                    "ใจสงบ",
                    "สมดุลชีวิต",
                    "ลดกังวล",
                    "พักผ่อน",
                    "inner peace",
                    "mindful living",
                    "calming music",
                    "thai dhamma",
                ]
            )

        return tags[:25]

    def _generate_hashtags(
        self, input_data: SeoMetadataInput, primary_keyword: str
    ) -> list[str]:
        hashtags: list[str] = []

        def add_hash(keyword: str) -> None:
            cleaned = keyword.replace(" ", "")
            if cleaned and f"#{cleaned}" not in hashtags:
                hashtags.append(f"#{cleaned}")

        add_hash("ธรรมะ")
        add_hash(primary_keyword)

        for keyword in input_data.primary_keywords[1:3]:
            add_hash(keyword)

        topic_terms = [term for term in re.split(r"\s+", input_data.topic_title) if term]
        for term in topic_terms[:2]:
            add_hash(term)

        add_hash("ธรรมะดีดี")
        add_hash("mindfulness")
        add_hash("sleepbetter")

        return hashtags[:8]

    def _truncate_text(self, text: str, limit: int) -> str:
        if len(text) <= limit:
            return text

        safe_limit = max(limit - 1, 1)
        truncated = text[:safe_limit]
        last_space = truncated.rfind(" ")
        if last_space > safe_limit * 0.6:
            truncated = truncated[:last_space]
        truncated = truncated.rstrip(" ,.;")
        if len(truncated) >= limit:
            truncated = truncated[: limit - 1]
        return f"{truncated}…"

    def _check_no_clickbait(self, title: str, description: str) -> bool:
        for phrase in self._clickbait_keywords:
            if phrase in title or phrase in description:
                return False
        return True
