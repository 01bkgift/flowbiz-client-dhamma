"""PersonalizationAgent - สร้างคำแนะนำเฉพาะบุคคล"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta
from statistics import mean
from typing import Literal

from automation_core.base_agent import BaseAgent

from .model import (
    EngagementMetrics,
    PersonalizationConfig,
    PersonalizationInput,
    PersonalizationMeta,
    PersonalizationOutput,
    PersonalizationRequest,
    PersonalizationSelfCheck,
    PersonalizedRecommendation,
    RecommendationItem,
    TrendInterest,
    ViewHistoryItem,
)


@dataclass
class _Candidate:
    """ข้อมูลชั่วคราวสำหรับจัดอันดับคำแนะนำ"""

    type: Literal["video", "topic", "feature"]
    confidence: float
    reason: str
    payload: dict


class PersonalizationAgent(BaseAgent[PersonalizationInput, PersonalizationOutput]):
    """Agent สำหรับสร้างคำแนะนำคอนเทนต์เฉพาะบุคคล"""

    VIDEO_LIBRARY: dict[str, list[dict[str, object]]] = {
        "นอนหลับ": [
            {
                "video_id": "V05",
                "title": "สมาธิก่อนนอน",
                "base_conf": 82.0,
                "angle": "ผ่อนคลายก่อนเข้านอน",
            },
            {
                "video_id": "V15",
                "title": "ปล่อยใจเบาก่อนหลับ",
                "base_conf": 76.0,
                "angle": "ปล่อยวางความคิดฟุ้งซ่าน",
            },
        ],
        "สมาธิ": [
            {
                "video_id": "V07",
                "title": "ฝึกสมาธิ 10 นาที",
                "base_conf": 78.0,
                "angle": "ฝึกสั้นๆ ทำได้ทุกวัน",
            },
            {
                "video_id": "V18",
                "title": "สมาธิเพื่อใจนิ่ง",
                "base_conf": 74.0,
                "angle": "เสริมวินัยและสติ",
            },
        ],
        "สุขภาพจิต": [
            {
                "video_id": "V22",
                "title": "ดูแลใจในวันที่เหนื่อย",
                "base_conf": 75.0,
                "angle": "ฟื้นแรงใจ",
            }
        ],
    }

    TOPIC_LIBRARY: dict[str, list[dict[str, object]]] = {
        "นอนหลับ": [
            {
                "topic": "Mindfulness สำหรับการนอน",
                "base_conf": 74.0,
                "insight": "เทรนด์การนอนหลับสูงและผู้ใช้สนใจ",
            }
        ],
        "สมาธิ": [
            {
                "topic": "คอร์สสมาธิ 7 วัน",
                "base_conf": 72.0,
                "insight": "ผู้ใช้ดูคอนเทนต์สมาธิจบเกิน 90%",
            }
        ],
        "สุขภาพจิต": [
            {
                "topic": "จัดการความเครียดในชีวิตประจำวัน",
                "base_conf": 70.0,
                "insight": "โปรไฟล์สนใจสุขภาพจิต",
            }
        ],
    }

    FEATURE_LIBRARY: dict[str, list[dict[str, object]]] = {
        "นอนหลับ": [
            {
                "feature": "playlist สมาธิก่อนนอน",
                "base_conf": 68.0,
                "insight": "ช่วยให้ผู้ใช้ฟังต่อเนื่อง",
            }
        ],
        "สมาธิ": [
            {
                "feature": "แจ้งเตือนฝึกสมาธิทุกเช้า",
                "base_conf": 66.0,
                "insight": "รักษาความสม่ำเสมอในการฝึก",
            }
        ],
        "สุขภาพจิต": [
            {
                "feature": "คอมมิวนิตี้แชร์ประสบการณ์",
                "base_conf": 64.0,
                "insight": "เปิดพื้นที่พูดคุยสุขภาพใจ",
            }
        ],
    }

    FALLBACK_VIDEO = {
        "video_id": "GEN01",
        "title": "ผ่อนคลายใจเบื้องต้น",
        "base_conf": 68.0,
        "angle": "ดูแลใจสำหรับทุกคน",
    }
    FALLBACK_TOPIC = {
        "topic": "ดูแลใจและสมาธิพื้นฐาน",
        "base_conf": 68.0,
        "insight": "หัวข้อกว้างที่ตอบโจทย์ผู้ชมส่วนใหญ่",
    }
    FALLBACK_FEATURE = {
        "feature": "playlist รวมธรรมะฟังสั้น",
        "base_conf": 65.0,
        "insight": "เพิ่มเวลาการรับชม",
    }

    RECENT_VIEW_THRESHOLD = 14
    COMPLETION_THRESHOLD = 90.0

    TREND_BOOST_CAP = 10.0
    TREND_BOOST_FACTOR = 0.12
    WATCH_BASELINE = 65.0
    WATCH_ADJUST_FACTOR = 0.15
    WATCH_ADJUST_FLOOR = -5.0
    HIGH_ENGAGEMENT_THRESHOLD = 10
    HIGH_ENGAGEMENT_BONUS = 4.0
    MODERATE_ENGAGEMENT_THRESHOLD = 5
    MODERATE_ENGAGEMENT_BONUS = 2.0

    def __init__(self) -> None:
        super().__init__(
            name="PersonalizationAgent",
            version="1.0.0",
            description="สร้างคำแนะนำเฉพาะบุคคลตามโปรไฟล์และพฤติกรรมผู้ชม",
        )

    def run(self, input_data: PersonalizationInput) -> PersonalizationOutput:
        request = input_data.personalization_request
        config = request.config

        recent_watched = self._recent_completed_videos(request)
        avg_watch = self._average_watch_pct(request.view_history)
        trend_lookup = self._trend_lookup(request.trend)
        engagement = request.engagement

        video_candidates = self._build_video_candidates(
            request, trend_lookup, avg_watch, recent_watched
        )
        topic_candidates = self._build_topic_candidates(
            request, trend_lookup, avg_watch
        )
        feature_candidates = self._build_feature_candidates(request, trend_lookup)

        selected = self._select_top_candidates(
            config, video_candidates, topic_candidates, feature_candidates
        )

        recommendations = self._to_recommendation_items(selected)
        action_plan = self._build_action_plan(recommendations)
        alerts = self._build_alerts(
            recommendations, config, request.view_history, engagement, avg_watch
        )

        meta = PersonalizationMeta(
            recommend_top_n=config.recommend_top_n,
            min_confidence_pct=config.min_confidence_pct,
            self_check=self._self_check(recommendations, action_plan),
        )

        personalized = PersonalizedRecommendation(
            recommend_to=request.user_id,
            recommendation=recommendations,
            action_plan=action_plan,
            alert=alerts,
            meta=meta,
        )
        return PersonalizationOutput(personalized_recommendation=[personalized])

    # ------------------------------------------------------------------
    # Candidate builders
    # ------------------------------------------------------------------
    def _build_video_candidates(
        self,
        request: PersonalizationRequest,
        trend_lookup: dict[str, float],
        avg_watch: float | None,
        recent_watched: set[str],
    ) -> list[_Candidate]:
        candidates: list[_Candidate] = []
        interests = request.profile.interest or list(trend_lookup.keys())

        for interest in interests:
            entries = self.VIDEO_LIBRARY.get(interest, [])
            if not entries:
                continue
            for entry in entries:
                video_id = str(entry["video_id"])
                if video_id in recent_watched:
                    continue
                base_conf = float(entry.get("base_conf", 65.0))
                confidence = self._apply_boosts(
                    base_conf,
                    trend_lookup.get(interest, 0.0),
                    avg_watch,
                    request.engagement,
                )
                reason_parts = [
                    f"สนใจหัวข้อ '{interest}'",
                ]
                if trend_lookup.get(interest):
                    reason_parts.append(f"เทรนด์คะแนน {trend_lookup[interest]:.0f}")
                if avg_watch is not None and avg_watch >= 80:
                    reason_parts.append(f"Retention เฉลี่ย {avg_watch:.0f}%")
                angle = entry.get("angle")
                if angle:
                    reason_parts.append(str(angle))
                reason = ", ".join(reason_parts)
                candidates.append(
                    _Candidate(
                        type="video",
                        confidence=confidence,
                        reason=reason,
                        payload={
                            "video_id": video_id,
                            "title": str(entry["title"]),
                        },
                    )
                )

        if not candidates:
            fallback_conf = self._apply_boosts(
                float(self.FALLBACK_VIDEO["base_conf"]),
                0.0,
                avg_watch,
                request.engagement,
            )
            reason = "คำแนะนำมาตรฐานสำหรับผู้ชมใหม่"
            candidates.append(
                _Candidate(
                    type="video",
                    confidence=fallback_conf,
                    reason=reason,
                    payload={
                        "video_id": str(self.FALLBACK_VIDEO["video_id"]),
                        "title": str(self.FALLBACK_VIDEO["title"]),
                    },
                )
            )
        return candidates

    def _build_topic_candidates(
        self,
        request: PersonalizationRequest,
        trend_lookup: dict[str, float],
        avg_watch: float | None,
    ) -> list[_Candidate]:
        candidates: list[_Candidate] = []
        for interest in request.profile.interest or list(trend_lookup.keys()):
            entries = self.TOPIC_LIBRARY.get(interest, [])
            for entry in entries:
                base_conf = float(entry.get("base_conf", 65.0))
                confidence = self._apply_boosts(
                    base_conf,
                    trend_lookup.get(interest, 0.0),
                    avg_watch,
                    request.engagement,
                )
                reason_parts = [str(entry.get("insight", ""))]
                if trend_lookup.get(interest):
                    reason_parts.append(f"เทรนด์ {trend_lookup[interest]:.0f} คะแนน")
                reason = ", ".join(part for part in reason_parts if part)
                candidates.append(
                    _Candidate(
                        type="topic",
                        confidence=confidence,
                        reason=reason or f"เกี่ยวข้องกับความสนใจ '{interest}'",
                        payload={"topic": str(entry["topic"])},
                    )
                )

        if not candidates:
            confidence = self._apply_boosts(
                float(self.FALLBACK_TOPIC["base_conf"]),
                0.0,
                avg_watch,
                request.engagement,
            )
            candidates.append(
                _Candidate(
                    type="topic",
                    confidence=confidence,
                    reason=str(self.FALLBACK_TOPIC["insight"]),
                    payload={"topic": str(self.FALLBACK_TOPIC["topic"])},
                )
            )
        return candidates

    def _build_feature_candidates(
        self,
        request: PersonalizationRequest,
        trend_lookup: dict[str, float],
    ) -> list[_Candidate]:
        candidates: list[_Candidate] = []
        for interest in request.profile.interest:
            entries = self.FEATURE_LIBRARY.get(interest, [])
            for entry in entries:
                base_conf = float(entry.get("base_conf", 60.0))
                confidence = self._apply_boosts(
                    base_conf,
                    trend_lookup.get(interest, 0.0),
                    None,
                    request.engagement,
                )
                reason = str(entry.get("insight", "")) or "สนับสนุนการมีส่วนร่วม"
                candidates.append(
                    _Candidate(
                        type="feature",
                        confidence=confidence,
                        reason=reason,
                        payload={"feature": str(entry["feature"])},
                    )
                )

        if not candidates:
            confidence = self._apply_boosts(
                float(self.FALLBACK_FEATURE["base_conf"]),
                0.0,
                None,
                request.engagement,
            )
            candidates.append(
                _Candidate(
                    type="feature",
                    confidence=confidence,
                    reason=str(self.FALLBACK_FEATURE["insight"]),
                    payload={"feature": str(self.FALLBACK_FEATURE["feature"])},
                )
            )
        return candidates

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _apply_boosts(
        self,
        base_conf: float,
        trend_score: float,
        avg_watch: float | None,
        engagement: EngagementMetrics,
    ) -> float:
        confidence = base_conf
        if trend_score:
            confidence += min(
                self.TREND_BOOST_CAP, trend_score * self.TREND_BOOST_FACTOR
            )
        if avg_watch is not None:
            confidence += max(
                self.WATCH_ADJUST_FLOOR,
                (avg_watch - self.WATCH_BASELINE) * self.WATCH_ADJUST_FACTOR,
            )
        if engagement.total >= self.HIGH_ENGAGEMENT_THRESHOLD:
            confidence += self.HIGH_ENGAGEMENT_BONUS
        elif engagement.total >= self.MODERATE_ENGAGEMENT_THRESHOLD:
            confidence += self.MODERATE_ENGAGEMENT_BONUS
        return max(0.0, min(100.0, confidence))

    def _recent_completed_videos(self, request: PersonalizationRequest) -> set[str]:
        cutoff = date.today() - timedelta(days=self.RECENT_VIEW_THRESHOLD)
        recent_completed = {
            item.video_id
            for item in request.view_history
            if item.watched_pct >= self.COMPLETION_THRESHOLD and item.date >= cutoff
        }
        return recent_completed

    def _average_watch_pct(
        self, view_history: Iterable[ViewHistoryItem]
    ) -> float | None:
        watched_values = [item.watched_pct for item in view_history]
        if not watched_values:
            return None
        return mean(watched_values)

    def _trend_lookup(self, trend: Iterable[TrendInterest]) -> dict[str, float]:
        return {item.topic: item.score for item in trend}

    def _select_top_candidates(
        self,
        config: PersonalizationConfig,
        videos: list[_Candidate],
        topics: list[_Candidate],
        features: list[_Candidate],
    ) -> list[_Candidate]:
        """Interleave ranked pools so recommendations mix formats naturally."""
        selected: list[_Candidate] = []
        ranked_videos = sorted(videos, key=lambda c: c.confidence, reverse=True)
        ranked_topics = sorted(topics, key=lambda c: c.confidence, reverse=True)
        ranked_features = sorted(features, key=lambda c: c.confidence, reverse=True)

        pools = [ranked_videos, ranked_topics, ranked_features]
        while len(selected) < config.recommend_top_n:
            made_a_selection = False
            for pool in pools:
                if not pool:
                    continue
                selected.append(pool.pop(0))
                made_a_selection = True
                if len(selected) == config.recommend_top_n:
                    break
            if not made_a_selection:
                break

        # หากยังไม่ครบ ให้ดึงจากแหล่งรวมทั้งหมดเรียงตามคะแนน
        if len(selected) < config.recommend_top_n:
            combined = ranked_videos + ranked_topics + ranked_features
            combined.sort(key=lambda c: c.confidence, reverse=True)
            for candidate in combined:
                if candidate in selected:
                    continue
                selected.append(candidate)
                if len(selected) >= config.recommend_top_n:
                    break

        return selected[: config.recommend_top_n]

    def _to_recommendation_items(
        self, candidates: list[_Candidate]
    ) -> list[RecommendationItem]:
        items: list[RecommendationItem] = []
        for idx, candidate in enumerate(candidates, start=1):
            payload = dict(candidate.payload)
            items.append(
                RecommendationItem(
                    type=candidate.type,
                    reason=candidate.reason,
                    confidence_pct=int(round(candidate.confidence)),
                    priority=idx,
                    **payload,
                )
            )
        return items

    def _build_action_plan(
        self, recommendations: list[RecommendationItem]
    ) -> list[str]:
        plan: list[str] = []
        for item in recommendations:
            if item.type == "video" and item.title:
                plan.append(f"ส่ง push notification โปรโมทวิดีโอ '{item.title}'")
            elif item.type == "topic" and item.topic:
                plan.append(f"วางแผนผลิตคอนเทนต์หัวข้อ '{item.topic}'")
            elif item.type == "feature" and item.feature:
                plan.append(f"นำเสนอฟีเจอร์ {item.feature} ในแคมเปญต่อไป")
        return plan

    def _build_alerts(
        self,
        recommendations: list[RecommendationItem],
        config: PersonalizationConfig,
        view_history: Iterable[ViewHistoryItem],
        engagement: EngagementMetrics,
        avg_watch: float | None,
    ) -> list[str]:
        alerts: list[str] = []
        history_list = list(view_history)
        for item in recommendations:
            if item.confidence_pct < config.min_confidence_pct:
                alerts.append(
                    f"ตรวจสอบคำแนะนำลำดับ {item.priority} ความมั่นใจ {item.confidence_pct}%"
                )
        if avg_watch is not None and avg_watch < 40:
            alerts.append("ผู้ใช้มี retention ต่ำกว่า 40% ต่อเนื่อง")
        if engagement.total < 2 and len(history_list) >= 2:
            alerts.append("engagement ต่ำ เสี่ยง disengaged")
        return alerts

    def _self_check(
        self, recommendations: list[RecommendationItem], action_plan: list[str]
    ) -> PersonalizationSelfCheck:
        has_all_sections = bool(recommendations)
        no_empty = all(rec.reason.strip() for rec in recommendations) and all(
            step.strip() for step in action_plan
        )
        return PersonalizationSelfCheck(
            all_sections_present=has_all_sections,
            no_empty_fields=no_empty,
        )
