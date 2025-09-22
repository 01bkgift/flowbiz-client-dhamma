"""
TopicPrioritizerAgent v1 - Agent สำหรับสร้าง Content Calendar

Agent นี้รับหัวข้อจาก TrendScout และสร้างปฏิทินการผลิตเนื้อหา
โดยจัดลำดับความสำคัญตามกลยุทธ์และกระจายเนื้อหาตลอด 4 สัปดาห์
"""

import logging
from datetime import datetime

from automation_core.base_agent import BaseAgent

from .model import (
    CandidateTopic,
    DiversitySummary,
    MetaInfo,
    # Legacy models for backward compatibility
    PrioritizedTopic,
    PriorityInput,
    PriorityOutput,
    ScheduledTopic,
    SelfCheck,
    UnscheduledTopic,
)

logger = logging.getLogger(__name__)


class TopicPrioritizerAgent(BaseAgent[PriorityInput, PriorityOutput]):
    """
    Agent สำหรับสร้าง Content Calendar จากหัวข้อ

    วิธีการทำงาน:
    1. รับหัวข้อผู้สมัครจาก TrendScout
    2. คำนวณคะแนนความสำคัญตามกลยุทธ์
    3. จำแนกประเภทเนื้อหา (longform/shorts)
    4. จัดสรรเนื้อหาในปฏิทิน 4 สัปดาห์
    5. ตรวจสอบความหลากหลายและข้อจำกัด
    """

    def __init__(self):
        super().__init__(
            name="TopicPrioritizerAgent",
            version="1.0.0",
            description="สร้าง Content Calendar จากหัวข้อตามกลยุทธ์ที่กำหนด",
        )

        # Default pillar performance ถ้าไม่มีข้อมูลประวัติ
        self.default_pillar_performance = {
            "ธรรมะประยุกต์": 1.05,
            "ชาดก/นิทานสอนใจ": 0.92,
            "ธรรมะสั้น": 1.10,
            "เจาะลึก/ซีรีส์": 1.18,
            "Q&A/ตอบคำถาม": 0.88,
            "สรุปพระสูตร/หนังสือ": 1.00,
        }

    def run(self, input_data: PriorityInput) -> PriorityOutput:
        """ประมวลผลการสร้าง Content Calendar"""

        logger.info(
            f"เริ่มสร้าง Content Calendar สำหรับ {len(input_data.candidate_topics)} หัวข้อ"
        )

        try:
            # 1. คำนวณคะแนนความสำคัญและจำแนกประเภท
            scored_topics = self._calculate_priority_scores(input_data)

            # 2. จัดสรรหัวข้อในปฏิทิน
            scheduled, unscheduled = self._assign_calendar(scored_topics, input_data)

            # 3. คำนวณสถิติและตรวจสอบ
            diversity_summary = self._calculate_diversity_summary(scheduled, input_data)
            self_check = self._perform_self_check(scheduled, unscheduled, input_data)

            # 4. สร้าง meta information
            meta = self._create_meta_info(
                input_data, scheduled, unscheduled, diversity_summary, self_check
            )

            result = PriorityOutput(
                plan_generated_at=datetime.now().isoformat(),
                strategy_focus=input_data.strategy_focus,
                weeks_capacity={
                    "longform_per_week": input_data.capacity.longform_per_week,
                    "shorts_per_week": input_data.capacity.shorts_per_week,
                },
                scheduled=scheduled,
                unscheduled=unscheduled,
                diversity_summary=diversity_summary,
                meta=meta,
            )

            logger.info(f"สร้าง Content Calendar เสร็จสิ้น - {len(scheduled)} หัวข้อในปฏิทิน")
            return result

        except Exception as e:
            logger.error(f"เกิดข้อผิดพลาดในการสร้าง Content Calendar: {e}")
            raise

    def _calculate_priority_scores(
        self, input_data: PriorityInput
    ) -> list[tuple[CandidateTopic, float, str, str]]:
        """คำนวณคะแนนความสำคัญสำหรับแต่ละหัวข้อ"""

        scored_topics = []
        max_predicted_views = (
            max(topic.predicted_14d_views for topic in input_data.candidate_topics)
            if input_data.candidate_topics
            else 1
        )

        historical_context = input_data.historical_context
        pillar_performance = (
            historical_context.pillar_performance
            if historical_context
            else self.default_pillar_performance
        )

        for topic in input_data.candidate_topics:
            # คำนวณ base score
            composite = topic.scores.get("composite", 0.5)
            normalized_views = min(1.0, topic.predicted_14d_views / max_predicted_views)
            base_score = composite * 70 + normalized_views * 30

            # ปรับตามกลยุทธ์
            adjustments = 0.0
            if input_data.strategy_focus == "fast_growth":
                adjustments += topic.scores.get("freshness", 0.5) * 10
                adjustments += topic.scores.get("search_intent", 0.5) * 5
            elif input_data.strategy_focus == "evergreen_balance":
                adjustments += topic.scores.get("evergreen", 0.5) * 8
                adjustments += topic.scores.get("brand_fit", 0.5) * 4
            elif input_data.strategy_focus == "depth_series":
                adjustments += topic.scores.get("brand_fit", 0.5) * 8
                adjustments += topic.scores.get("evergreen", 0.5) * 6
                # Series bonus
                if any(
                    topic.title.startswith(prefix)
                    for prefix in input_data.rules.force_series_prefixes
                ):
                    adjustments += 6

            # ปรับตาม pillar performance
            pillar_factor = pillar_performance.get(topic.pillar, 1.0)
            final_score = (base_score + adjustments) * pillar_factor
            final_score = max(0, min(100, final_score))  # Clip ให้อยู่ใน 0-100

            # จำแนกประเภทเนื้อหา
            content_type = self._classify_content_type(topic, input_data)

            # กำหนดบทบาทที่คาดหวัง
            expected_role = self._determine_expected_role(
                topic, input_data.strategy_focus, final_score
            )

            scored_topics.append((topic, final_score, content_type, expected_role))

        # เรียงลำดับตามคะแนน
        scored_topics.sort(key=lambda x: x[1], reverse=True)

        return scored_topics

    def _classify_content_type(
        self, topic: CandidateTopic, input_data: PriorityInput
    ) -> str:
        """จำแนกประเภทเนื้อหา (longform หรือ shorts)"""

        historical_context = input_data.historical_context
        recent_longform_avg = (
            historical_context.recent_longform_avg_views if historical_context else 3200
        )

        # ตรวจสอบเงื่อนไข force_series_prefixes
        if any(
            topic.title.startswith(prefix)
            for prefix in input_data.rules.force_series_prefixes
        ):
            return "longform"

        # ตรวจสอบความลึกและยอดวิว
        evergreen = topic.scores.get("evergreen", 0.5)
        brand_fit = topic.scores.get("brand_fit", 0.5)
        search_intent = topic.scores.get("search_intent", 0.5)

        if (
            evergreen > 0.65 or brand_fit > 0.85
        ) and topic.predicted_14d_views >= recent_longform_avg:
            return "longform"
        elif search_intent > 0.7 and evergreen < 0.55:
            return "shorts"
        else:
            # Default decision based on predicted views
            return (
                "longform"
                if topic.predicted_14d_views >= recent_longform_avg
                else "shorts"
            )

    def _determine_expected_role(
        self, topic: CandidateTopic, strategy: str, score: float
    ) -> str:
        """กำหนดบทบาทที่คาดหวัง"""

        freshness = topic.scores.get("freshness", 0.5)
        evergreen = topic.scores.get("evergreen", 0.5)

        if strategy == "fast_growth" and freshness > 0.7:
            return "traffic_spike"
        elif evergreen > 0.7:
            return "evergreen_seed"
        elif any(
            topic.title.startswith(prefix)
            for prefix in ["พุทธจิตวิทยา", "ชาดกชุด", "10 วันภาวนา"]
        ):
            return "series_part"
        elif score > 70:
            return "audience_engagement"
        else:
            return "balance_filler"

    def _assign_calendar(
        self,
        scored_topics: list[tuple[CandidateTopic, float, str, str]],
        input_data: PriorityInput,
    ) -> tuple[list[ScheduledTopic], list[UnscheduledTopic]]:
        """จัดสรรหัวข้อในปฏิทิน"""

        scheduled = []
        unscheduled = []

        # ข้อมูลการใช้งาน capacity
        weeks_usage = {
            f"W{i}": {"longform": 0, "shorts": 0}
            for i in range(1, input_data.capacity.weeks + 1)
        }

        current_week = 1
        slot_counters = {f"W{i}": 1 for i in range(1, input_data.capacity.weeks + 1)}

        for topic, score, content_type, expected_role in scored_topics:
            # ตรวจสอบคะแนนต่ำ
            if score < 40:
                unscheduled.append(
                    UnscheduledTopic(
                        topic_title=topic.title,
                        reason="low_score",
                        priority_score=score,
                    )
                )
                continue

            # หาสัปดาห์ที่มีที่ว่าง
            week_assigned = None
            for week in [
                f"W{i}" for i in range(current_week, input_data.capacity.weeks + 1)
            ]:
                if content_type == "longform":
                    if (
                        weeks_usage[week]["longform"]
                        < input_data.capacity.longform_per_week
                    ):
                        week_assigned = week
                        weeks_usage[week]["longform"] += 1
                        break
                else:  # shorts
                    if (
                        weeks_usage[week]["shorts"]
                        < input_data.capacity.shorts_per_week
                    ):
                        week_assigned = week
                        weeks_usage[week]["shorts"] += 1
                        break

            # ลองหาจากสัปดาห์แรกอีกครั้ง
            if not week_assigned:
                for week in [f"W{i}" for i in range(1, current_week)]:
                    if content_type == "longform":
                        if (
                            weeks_usage[week]["longform"]
                            < input_data.capacity.longform_per_week
                        ):
                            week_assigned = week
                            weeks_usage[week]["longform"] += 1
                            break
                    else:  # shorts
                        if (
                            weeks_usage[week]["shorts"]
                            < input_data.capacity.shorts_per_week
                        ):
                            week_assigned = week
                            weeks_usage[week]["shorts"] += 1
                            break

            if week_assigned:
                # จัดกลุ่มซีรีส์
                series_group = None
                risk_flags = []

                for prefix in input_data.rules.force_series_prefixes:
                    if topic.title.startswith(prefix):
                        series_group = prefix
                        break

                # สร้างหมายเหตุ
                notes = self._generate_notes(
                    topic, expected_role, input_data.strategy_focus
                )

                scheduled.append(
                    ScheduledTopic(
                        topic_title=topic.title,
                        content_type=content_type,
                        pillar=topic.pillar,
                        week=week_assigned,
                        slot_index=slot_counters[week_assigned],
                        priority_score=score,
                        expected_role=expected_role,
                        series_group=series_group,
                        risk_flags=risk_flags,
                        notes=notes,
                    )
                )

                slot_counters[week_assigned] += 1

                # ปรับ current_week สำหรับรอบถัดไป
                if current_week <= input_data.capacity.weeks:
                    current_week = (current_week % input_data.capacity.weeks) + 1
            else:
                unscheduled.append(
                    UnscheduledTopic(
                        topic_title=topic.title,
                        reason="capacity_full",
                        priority_score=score,
                    )
                )

        return scheduled, unscheduled

    def _generate_notes(
        self, topic: CandidateTopic, expected_role: str, strategy: str
    ) -> str:
        """สร้างหมายเหตุสำหรับหัวข้อ"""

        notes = []

        if expected_role == "traffic_spike":
            notes.append("คาดหวังยอดวิวสูง")
        elif expected_role == "series_part":
            notes.append("ส่วนหนึ่งของซีรีส์")

        if strategy == "fast_growth":
            freshness = topic.scores.get("freshness", 0.5)
            if freshness > 0.8:
                notes.append("สดใหม่สูง เหมาะเปิดเดือน")

        if topic.predicted_14d_views > 10000:
            notes.append("คาดการณ์ยอดวิวสูง")

        return " | ".join(notes) if notes else "ปกติ"

    def _calculate_diversity_summary(
        self, scheduled: list[ScheduledTopic], input_data: PriorityInput
    ) -> DiversitySummary:
        """คำนวณสรุปความหลากหลาย"""

        pillar_counts = {}
        for topic in scheduled:
            pillar_counts[topic.pillar] = pillar_counts.get(topic.pillar, 0) + 1

        distinct_pillars = len(pillar_counts)
        meets_minimum = distinct_pillars >= input_data.rules.min_pillars_diversity

        return DiversitySummary(
            pillar_counts=pillar_counts,
            distinct_pillars=distinct_pillars,
            meets_minimum=meets_minimum,
        )

    def _perform_self_check(
        self,
        scheduled: list[ScheduledTopic],
        unscheduled: list[UnscheduledTopic],
        input_data: PriorityInput,
    ) -> SelfCheck:
        """ตรวจสอบผลลัพธ์ด้วยตัวเอง"""

        # ตรวจสอบ capacity
        weeks_usage = {}
        for topic in scheduled:
            if topic.week not in weeks_usage:
                weeks_usage[topic.week] = {"longform": 0, "shorts": 0}
            weeks_usage[topic.week][topic.content_type] += 1

        capacity_respected = True
        for _week, usage in weeks_usage.items():
            if (
                usage["longform"] > input_data.capacity.longform_per_week
                or usage["shorts"] > input_data.capacity.shorts_per_week
            ):
                capacity_respected = False
                break

        # ตรวจสอบการเรียงลำดับคะแนน (อนุโลม)
        longform_scores = [
            t.priority_score for t in scheduled if t.content_type == "longform"
        ]
        shorts_scores = [
            t.priority_score for t in scheduled if t.content_type == "shorts"
        ]

        scores_monotonic = True
        if len(longform_scores) > 1:
            scores_monotonic = scores_monotonic and all(
                longform_scores[i] >= longform_scores[i + 1]
                for i in range(len(longform_scores) - 1)
            )
        if len(shorts_scores) > 1:
            scores_monotonic = scores_monotonic and all(
                shorts_scores[i] >= shorts_scores[i + 1]
                for i in range(len(shorts_scores) - 1)
            )

        # ตรวจสอบความหลากหลาย
        pillars = {t.pillar for t in scheduled}
        diversity_ok = len(pillars) >= input_data.rules.min_pillars_diversity

        return SelfCheck(
            capacity_respected=capacity_respected,
            scores_monotonic=scores_monotonic,
            diversity_ok=diversity_ok,
        )

    def _create_meta_info(
        self,
        input_data: PriorityInput,
        scheduled: list[ScheduledTopic],
        unscheduled: list[UnscheduledTopic],
        diversity_summary: DiversitySummary,
        self_check: SelfCheck,
    ) -> MetaInfo:
        """สร้างข้อมูล Meta"""

        # หา pillar ที่มีสัดส่วนน้อย
        all_pillars = {topic.pillar for topic in input_data.candidate_topics}
        scheduled_pillars = {topic.pillar for topic in scheduled}
        underrepresented = list(all_pillars - scheduled_pillars)

        # สร้างหมายเหตุการปรับแต่ง
        adjustments_notes = f"{input_data.strategy_focus} emphasis"
        if input_data.strategy_focus == "fast_growth":
            adjustments_notes += " -> freshness weighted"
        elif input_data.strategy_focus == "evergreen_balance":
            adjustments_notes += " -> balanced approach"
        elif input_data.strategy_focus == "depth_series":
            adjustments_notes += " -> series and depth prioritized"

        return MetaInfo(
            total_candidates=len(input_data.candidate_topics),
            scheduled_count=len(scheduled),
            unscheduled_count=len(unscheduled),
            pillars_underrepresented=underrepresented,
            adjustments_notes=adjustments_notes,
            self_check=self_check,
        )

    # Legacy methods for backward compatibility
    def _generate_recommendations(
        self, prioritized_topics: list[PrioritizedTopic], input_data: PriorityInput
    ) -> list[str]:
        """สร้างคำแนะนำสำหรับการผลิต (Legacy)"""

        recommendations = []

        if len(prioritized_topics) > 0:
            top_topic = prioritized_topics[0]
            recommendations.append(
                f"แนะนำให้ผลิต '{top_topic.original_topic.title}' เป็นอันดับแรก"
            )

            if top_topic.priority_scores.production_difficulty < 50:
                recommendations.append("ควรจัดทีมที่มีประสบการณ์สำหรับหัวข้อแรก")

            high_risk_count = sum(
                1 for t in prioritized_topics[:5] if t.priority_scores.risk_level < 50
            )
            if high_risk_count > 2:
                recommendations.append("พิจารณาลดความเสี่ยงในหัวข้อ Top 5")

            diversity_score = len(
                {t.original_topic.pillar for t in prioritized_topics[:5]}
            )
            if diversity_score < 3:
                recommendations.append("ควรเพิ่มความหลากหลายของเนื้อหา")

        return recommendations
