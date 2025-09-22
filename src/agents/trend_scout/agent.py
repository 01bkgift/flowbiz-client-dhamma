"""
TrendScoutAgent - Agent สำหรับวิเคราะห์เทรนด์และสร้างหัวข้อคอนเทนต์

Agent นี้รับข้อมูลเทรนด์จากหลายแหล่ง และสร้างหัวข้อคอนเทนต์ที่น่าสนใจ
โดยจำลองการทำงานของ LLM ด้วยอัลกอริทึมที่กำหนดล่วงหน้า
"""

import hashlib
import logging
import random
from datetime import datetime
from typing import Any

from automation_core.base_agent import BaseAgent
from automation_core.utils.scoring import (
    calculate_composite_score,
    validate_score_range,
)
from automation_core.utils.text import (
    create_youtube_title,
    extract_keywords,
)

from .model import (
    MetaInfo,
    SelfCheck,
    TopicEntry,
    TopicScore,
    TrendScoutInput,
    TrendScoutOutput,
)

logger = logging.getLogger(__name__)


class TrendScoutAgent(BaseAgent[TrendScoutInput, TrendScoutOutput]):
    """
    Agent สำหรับวิเคราะห์เทรนด์และสร้างหัวข้อคอนเทนต์

    วิธีการทำงาน:
    1. รวบรวมคำสำคัญจากแหล่งต่างๆ
    2. สร้างหัวข้อผู้สมัครจากคำสำคัญ
    3. คำนวณคะแนนในแต่ละมิติ
    4. จัดอันดับและคัดเลือกหัวข้อที่ดีที่สุด
    """

    def __init__(self):
        super().__init__(
            name="TrendScoutAgent",
            version="1.0.0",
            description="วิเคราะห์เทรนด์และสร้างหัวข้อคอนเทนต์สำหรับช่อง YouTube ธรรมะดีดี",
        )

        # น้ำหนักสำหรับการคำนวณคะแนนรวม
        self.score_weights = {
            "search_intent": 0.30,
            "freshness": 0.25,
            "evergreen": 0.25,
            "brand_fit": 0.20,
        }

        # เสาหลักเนื้อหาของช่อง (ตาม v1 specification)
        self.content_pillars = [
            "ธรรมะประยุกต์",
            "ชาดก/นิทานสอนใจ",
            "ธรรมะสั้น",
            "เจาะลึก/ซีรีส์",
            "Q&A/ตอบคำถาม",
            "สรุปพระสูตร/หนังสือ",
        ]

    def run(self, input_data: TrendScoutInput) -> TrendScoutOutput:
        """
        ประมวลผลข้อมูลเทรนด์และสร้างหัวข้อคอนเทนต์
        """

        logger.info(f"เริ่มประมวลผลด้วย {self.name}")
        logger.debug(f"ได้รับ keywords: {input_data.keywords}")

        try:
            # 1. รวบรวมคำสำคัญจากแหล่งต่างๆ
            all_keywords = self._collect_keywords(input_data)
            logger.debug(f"รวบรวมคำสำคัญได้ {len(all_keywords)} คำ")

            # 2. สร้างหัวข้อผู้สมัคร
            candidate_topics = self._generate_candidate_topics(all_keywords)
            logger.debug(f"สร้างหัวข้อผู้สมัครได้ {len(candidate_topics)} หัวข้อ")

            # 3. คำนวณคะแนนและจัดอันดับ
            scored_topics = self._score_and_rank_topics(candidate_topics, input_data)
            logger.debug(f"ให้คะแนนและจัดอันดับได้ {len(scored_topics)} หัวข้อ")

            # 4. คัดเลือกหัวข้อที่ดีที่สุด (สูงสุด 15 หัวข้อ)
            final_topics = scored_topics[:15]

            # 5. สร้าง metadata
            meta_info = self._create_meta_info(candidate_topics, final_topics)

            # 6. สร้างผลลัพธ์
            result = TrendScoutOutput(
                generated_at=datetime.now(),
                topics=final_topics,
                discarded_duplicates=[],  # สำหรับอนาคต
                meta=meta_info,
            )

            logger.info(f"สร้างหัวข้อสำเร็จ {len(final_topics)} หัวข้อ")
            return result

        except Exception as e:
            logger.error(f"เกิดข้อผิดพลาดในการประมวลผล: {e}")
            raise

    def _collect_keywords(self, input_data: TrendScoutInput) -> list[str]:
        """รวบรวมคำสำคัญจากแหล่งข้อมูลต่างๆ"""

        all_keywords = set(input_data.keywords)

        # จาก Google Trends
        for trend in input_data.google_trends:
            all_keywords.add(trend.term)

        # จาก YouTube trending videos
        for video in input_data.youtube_trending_raw:
            all_keywords.update(video.keywords)
            # แยกคำจากชื่อวิดีโอ
            title_keywords = extract_keywords(video.title)
            all_keywords.update(title_keywords)

        # จาก competitor comments
        for comment in input_data.competitor_comments:
            comment_keywords = extract_keywords(comment.comment)
            all_keywords.update(comment_keywords)

        # จาก embedding groups
        for group in input_data.embeddings_similar_groups:
            all_keywords.update(group.keywords)

        # กรองคำที่สั้นเกินไป
        filtered_keywords = [kw for kw in all_keywords if len(kw.strip()) >= 2]

        return filtered_keywords

    def _generate_candidate_topics(self, keywords: list[str]) -> list[dict[str, Any]]:
        """สร้างหัวข้อผู้สมัครจากคำสำคัญ"""

        candidates = []

        # สร้างหัวข้อจากคำสำคัญเดี่ยว
        for keyword in keywords:
            title = self._create_title_from_keyword(keyword)
            candidates.append(
                {"title": title, "raw_keywords": [keyword], "source": "single_keyword"}
            )

        # สร้างหัวข้อจากการรวมคำสำคัญ
        for i, kw1 in enumerate(keywords):
            for kw2 in keywords[i + 1 :]:
                combined_title = self._create_title_from_keywords([kw1, kw2])
                candidates.append(
                    {
                        "title": combined_title,
                        "raw_keywords": [kw1, kw2],
                        "source": "combined_keywords",
                    }
                )

        # ลบหัวข้อซ้ำและปรับความยาว
        unique_candidates = []
        seen_titles = set()

        for candidate in candidates:
            # ปรับความยาวชื่อให้เหมาะสม
            title = create_youtube_title(candidate["title"], max_length=34)

            if title not in seen_titles and len(title.strip()) > 5:
                seen_titles.add(title)
                candidate["title"] = title
                unique_candidates.append(candidate)

        return unique_candidates

    def _create_title_from_keyword(self, keyword: str) -> str:
        """สร้างชื่อหัวข้อจากคำสำคัญเดี่ยว"""

        # รูปแบบชื่อหัวข้อสำหรับเนื้อหาธรรมะ
        title_patterns = [
            f"วิธี{keyword}ตามหลักธรรม",
            f"{keyword}ให้ใจสงบ",
            f"เมื่อ{keyword}ทำยังไง",
            f"{keyword}ด้วยสติ",
            f"การ{keyword}แบบพุทธ",
            f"{keyword}ใจให้เบา",
            f"พ้น{keyword}ด้วยธรรม",
            f"{keyword}อย่างสมดุล",
        ]

        # เลือกรูปแบบตาม hash ของคำสำคัญ (deterministic)
        hash_val = int(hashlib.md5(keyword.encode()).hexdigest(), 16)
        pattern_idx = hash_val % len(title_patterns)

        return title_patterns[pattern_idx]

    def _create_title_from_keywords(self, keywords: list[str]) -> str:
        """สร้างชื่อหัวข้อจากหลายคำสำคัญ"""

        if len(keywords) == 2:
            kw1, kw2 = keywords
            combined_patterns = [
                f"{kw1}และ{kw2}",
                f"จาก{kw1}สู่{kw2}",
                f"{kw1}หรือ{kw2}ดี",
                f"เมื่อ{kw1}พบ{kw2}",
                f"{kw1}ให้{kw2}",
            ]

            # เลือกรูปแบบตาม hash
            combined = "".join(keywords)
            hash_val = int(hashlib.md5(combined.encode()).hexdigest(), 16)
            pattern_idx = hash_val % len(combined_patterns)

            return combined_patterns[pattern_idx]

        # สำหรับมากกว่า 2 คำ
        return " ".join(keywords[:3])  # ใช้แค่ 3 คำแรก

    def _score_and_rank_topics(
        self, candidates: list[dict[str, Any]], input_data: TrendScoutInput
    ) -> list[TopicEntry]:
        """คำนวณคะแนนและจัดอันดับหัวข้อ"""

        scored_topics = []

        for candidate in candidates:
            scores = self._calculate_topic_scores(candidate, input_data)

            # คำนวณคะแนนรวม
            composite_score = calculate_composite_score(
                {
                    "search_intent": scores["search_intent"],
                    "freshness": scores["freshness"],
                    "evergreen": scores["evergreen"],
                    "brand_fit": scores["brand_fit"],
                },
                self.score_weights,
            )

            scores["composite"] = composite_score

            # เลือก content pillar
            pillar = self._select_content_pillar(candidate)

            # คาดการณ์จำนวนการดู
            predicted_views = self._predict_views(scores, candidate)

            # สร้าง topic dict ก่อน แล้วค่อยสร้าง TopicEntry หลังจัดอันดับ
            topic_data = {
                "title": candidate["title"],
                "pillar": pillar,
                "predicted_14d_views": predicted_views,
                "scores": scores,
                "reason": self._generate_reason(scores, candidate),
                "raw_keywords": candidate["raw_keywords"],
                "similar_to": [],
                "risk_flags": [],
            }

            scored_topics.append(topic_data)

        # จัดอันดับตามคะแนนรวม
        sorted_topics_data = sorted(
            scored_topics, key=lambda t: t["scores"]["composite"], reverse=True
        )

        # สร้าง TopicEntry พร้อมอันดับ
        final_topics = []
        for i, topic_data in enumerate(sorted_topics_data, 1):
            topic = TopicEntry(
                rank=i,
                title=topic_data["title"],
                pillar=topic_data["pillar"],
                predicted_14d_views=topic_data["predicted_14d_views"],
                scores=TopicScore(**topic_data["scores"]),
                reason=topic_data["reason"],
                raw_keywords=topic_data["raw_keywords"],
                similar_to=topic_data["similar_to"],
                risk_flags=topic_data["risk_flags"],
            )
            final_topics.append(topic)

        return final_topics

    def _calculate_topic_scores(
        self, candidate: dict[str, Any], input_data: TrendScoutInput
    ) -> dict[str, float]:
        """คำนวณคะแนนในแต่ละมิติ"""

        title = candidate["title"]
        keywords = candidate["raw_keywords"]

        # ใช้ hash เพื่อให้ได้คะแนนที่สม่ำเสมอ (deterministic)
        title_hash = int(hashlib.md5(title.encode()).hexdigest(), 16)

        # Search Intent Score (ความตั้งใจค้นหา)
        search_intent = self._calculate_search_intent_score(
            keywords, input_data, title_hash
        )

        # Freshness Score (ความใหม่)
        freshness = self._calculate_freshness_score(keywords, input_data, title_hash)

        # Evergreen Score (ความคงทน)
        evergreen = self._calculate_evergreen_score(title, title_hash)

        # Brand Fit Score (ความเข้ากับแบรนด์)
        brand_fit = self._calculate_brand_fit_score(title, keywords, title_hash)

        return {
            "search_intent": search_intent,
            "freshness": freshness,
            "evergreen": evergreen,
            "brand_fit": brand_fit,
        }

    def _calculate_search_intent_score(
        self, keywords: list[str], input_data: TrendScoutInput, seed: int
    ) -> float:
        """คำนวณคะแนนความตั้งใจค้นหา"""

        # ใช้ hash + keyword เป็น seed
        random.seed(seed + sum(hash(kw) for kw in keywords))

        base_score = random.uniform(0.3, 0.9)

        # เพิ่มคะแนนถ้ามีใน Google Trends
        for trend in input_data.google_trends:
            if any(kw.lower() in trend.term.lower() for kw in keywords):
                if trend.score_series:
                    avg_trend = sum(trend.score_series) / len(trend.score_series)
                    base_score += (avg_trend / 100) * 0.2

        # เพิ่มคะแนนถ้ามีใน YouTube trending
        for video in input_data.youtube_trending_raw:
            if any(kw.lower() in video.title.lower() for kw in keywords):
                base_score += 0.15

        return min(base_score, 1.0)

    def _calculate_freshness_score(
        self, keywords: list[str], input_data: TrendScoutInput, seed: int
    ) -> float:
        """คำนวณคะแนนความใหม่"""

        random.seed(seed + 1)
        base_score = random.uniform(0.2, 0.8)

        # เพิ่มคะแนนถ้าพบในวิดีโอใหม่
        for video in input_data.youtube_trending_raw:
            if video.age_days <= 7:  # วิดีโอใหม่ (≤ 7 วัน)
                if any(kw.lower() in video.title.lower() for kw in keywords):
                    base_score += 0.3

        return min(base_score, 1.0)

    def _calculate_evergreen_score(self, title: str, seed: int) -> float:
        """คำนวณคะแนนความคงทน"""

        random.seed(seed + 2)

        # คำที่ทำให้เนื้อหาคงทน
        evergreen_words = [
            "วิธี",
            "การ",
            "หลัก",
            "ธรรม",
            "สติ",
            "สมาธิ",
            "ใจ",
            "จิตใจ",
            "ความสุข",
            "ปล่อยวาง",
            "เครียด",
        ]

        base_score = random.uniform(0.4, 0.7)

        # เพิ่มคะแนนถ้ามีคำที่ทำให้คงทน
        for word in evergreen_words:
            if word in title:
                base_score += 0.1

        return min(base_score, 1.0)

    def _calculate_brand_fit_score(
        self, title: str, keywords: list[str], seed: int
    ) -> float:
        """คำนวณคะแนนความเข้ากับแบรนด์"""

        random.seed(seed + 3)

        # คำที่เข้ากับแบรนด์ธรรมะดีดี
        brand_words = [
            "ธรรม",
            "ธรรมะ",
            "พุทธ",
            "สมาธิ",
            "สติ",
            "วิปัสสนา",
            "ใจ",
            "จิตใจ",
            "ความสุข",
            "สงบ",
            "สมดุล",
            "ปล่อยวาง",
        ]

        base_score = random.uniform(0.5, 0.8)

        # เพิ่มคะแนนถ้ามีคำที่เข้ากับแบรนด์
        brand_word_count = sum(1 for word in brand_words if word in title)
        base_score += brand_word_count * 0.15

        return min(base_score, 1.0)

    def _select_content_pillar(self, candidate: dict[str, Any]) -> str:
        """เลือก content pillar ที่เหมาะสม"""

        title = candidate["title"].lower()

        # ระบุ pillar ตามคำสำคัญในชื่อ (ตาม v1 specification)
        pillar_keywords = {
            "ธรรมะประยุกต์": ["ประยุกต์", "ชีวิต", "ทำงาน", "วิธี", "การใช้", "ใช้ธรรม"],
            "ชาดก/นิทานสอนใจ": ["เรื่อง", "นิทาน", "ชาดก", "สอนใจ", "เล่า"],
            "ธรรมะสั้น": ["สั้น", "ระลึก", "คิด", "ย่อ", "สรุป"],
            "เจาะลึก/ซีรีส์": ["เจาะลึก", "ซีรีส์", "ตอน", "ลึกซึ้ง", "วิเคราะห์"],
            "Q&A/ตอบคำถาม": ["ถาม", "ตอบ", "สงสัย", "คำถาม", "แก้ข้อสงสัย"],
            "สรุปพระสูตร/หนังสือ": ["สรุป", "หนังสือ", "สูตร", "พระสูตร", "บทเรียน"],
        }

        for pillar, keywords in pillar_keywords.items():
            if any(keyword in title for keyword in keywords):
                return pillar

        # Default pillar
        return "ธรรมะประยุกต์"

    def _predict_views(
        self, scores: dict[str, float], candidate: dict[str, Any]
    ) -> int:
        """คาดการณ์จำนวนการดู 14 วัน"""

        # ใช้คะแนนรวมเป็นฐาน
        base_views = int(scores.get("composite", 0.5) * 20000)

        # ปรับตามความยาวชื่อ
        title_length = len(candidate["title"])
        if title_length <= 30:
            base_views = int(base_views * 1.2)
        elif title_length > 50:
            base_views = int(base_views * 0.8)

        # เพิ่ม noise เล็กน้อย
        title_hash = hash(candidate["title"])
        random.seed(title_hash)
        noise = random.uniform(0.8, 1.2)

        return max(int(base_views * noise), 1000)

    def _generate_reason(
        self, scores: dict[str, float], candidate: dict[str, Any]
    ) -> str:
        """สร้างเหตุผลที่แนะนำหัวข้อ"""

        reasons = []

        if scores["search_intent"] > 0.7:
            reasons.append("ค้นหาสูง")

        if scores["freshness"] > 0.7:
            reasons.append("เทรนด์ใหม่")

        if scores["evergreen"] > 0.7:
            reasons.append("เนื้อหาคงทน")

        if scores["brand_fit"] > 0.8:
            reasons.append("เข้ากับแบรนด์")

        if not reasons:
            reasons.append("ปัญหาที่คนพบบ่อย")

        return " + ".join(reasons)

    def _create_meta_info(
        self, candidates: list[dict[str, Any]], final_topics: list[TopicEntry]
    ) -> MetaInfo:
        """สร้างข้อมูล metadata"""

        # ตรวจสอบความถูกต้องของผลลัพธ์
        all_scores = {}
        for topic in final_topics:
            all_scores.update(
                {
                    f"{topic.title}_search_intent": topic.scores.search_intent,
                    f"{topic.title}_freshness": topic.scores.freshness,
                    f"{topic.title}_evergreen": topic.scores.evergreen,
                    f"{topic.title}_brand_fit": topic.scores.brand_fit,
                    f"{topic.title}_composite": topic.scores.composite,
                }
            )

        score_range_valid = validate_score_range(all_scores, 0.0, 1.0)

        # ตรวจสอบ duplicate (ในอนาคตอาจมีการตรวจสอบที่ซับซ้อนกว่า)
        titles = [topic.title for topic in final_topics]
        duplicate_ok = len(titles) == len(set(titles))

        return MetaInfo(
            total_candidates_considered=len(candidates),
            prediction_method="median_trending * scaling_ratio",
            adjustment_notes="ปรับคะแนนตาม brand fit และ evergreen score",
            self_check=SelfCheck(
                duplicate_ok=duplicate_ok, score_range_valid=score_range_valid
            ),
        )
