"""Scheduling & Publishing agent implementation."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from automation_core.base_agent import BaseAgent

from .model import (
    AudienceAnalytics,
    ContentCalendarEntry,
    ScheduleConstraints,
    ScheduleEntry,
    ScheduleMeta,
    SchedulingInput,
    SchedulingOutput,
    SelfCheck,
)


@dataclass
class CandidateSlot:
    """Represents a candidate slot for scheduling."""

    week_index: int
    local_datetime: datetime
    utc_datetime: datetime
    reason: str


class SchedulingPublishingAgent(BaseAgent[SchedulingInput, SchedulingOutput]):
    """Agent responsible for scheduling and publishing automation."""

    def __init__(self) -> None:
        super().__init__(
            name="SchedulingPublishingAgent",
            version="1.0.0",
            description="จัดตารางเผยแพร่วิดีโอและเตรียมข้อมูล auto-publish",
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def run(self, input_data: SchedulingInput) -> SchedulingOutput:
        """Generate scheduling plan based on constraints and analytics."""

        timezone_info = ZoneInfo(input_data.audience_analytics.timezone)
        base_monday = self._determine_base_monday(input_data, timezone_info)

        sorted_entries = sorted(
            input_data.content_calendar,
            key=lambda entry: (-entry.priority_score, entry.video_id),
        )

        week_usage: dict[int, dict[str, int]] = defaultdict(
            lambda: {"longform": 0, "shorts": 0, "live": 0, "audio": 0}
        )
        day_usage: dict[date, int] = defaultdict(int)
        scheduled_items: list[ScheduleEntry] = []
        scheduled_slots: list[tuple[str, datetime]] = []  # (pillar, utc_dt)
        warnings: list[str] = []

        for entry in sorted_entries:
            if not entry.ready_to_publish:
                scheduled_items.append(
                    ScheduleEntry(
                        video_id=entry.video_id,
                        topic_title=entry.topic_title,
                        scheduled_datetime_utc=None,
                        scheduled_datetime_local=None,
                        publish_status="pending",
                        pillar=entry.pillar,
                        content_type=entry.content_type,
                        priority_score=entry.priority_score,
                        reason="รอความพร้อมจากทีมผลิต",
                        collision_with=None,
                        overflow_reason=None,
                        auto_publish_ready=False,
                    )
                )
                continue

            candidate = self._find_slot(
                entry,
                input_data.constraints,
                input_data.audience_analytics,
                base_monday,
                week_usage,
                day_usage,
                scheduled_slots,
                timezone_info,
            )

            if candidate:
                # Update usage counters
                usage = week_usage[candidate.week_index]
                usage[entry.content_type] += 1
                day_usage[candidate.local_datetime.date()] += 1
                scheduled_slots.append((entry.pillar, candidate.utc_datetime))

                scheduled_items.append(
                    ScheduleEntry(
                        video_id=entry.video_id,
                        topic_title=entry.topic_title,
                        scheduled_datetime_utc=candidate.utc_datetime,
                        scheduled_datetime_local=candidate.local_datetime,
                        publish_status="scheduled",
                        pillar=entry.pillar,
                        content_type=entry.content_type,
                        priority_score=entry.priority_score,
                        reason=candidate.reason,
                        collision_with=None,
                        overflow_reason=None,
                        auto_publish_ready=True,
                    )
                )
            else:
                # Check if conflict due to collision and fallback slot exists
                collision_slot = self._find_collision_slot(
                    entry,
                    input_data.constraints,
                    input_data.audience_analytics,
                    base_monday,
                    week_usage,
                    day_usage,
                    scheduled_slots,
                    timezone_info,
                )

                if collision_slot:
                    usage = week_usage[collision_slot.week_index]
                    usage[entry.content_type] += 1
                    day_usage[collision_slot.local_datetime.date()] += 1
                    scheduled_slots.append((entry.pillar, collision_slot.utc_datetime))

                    conflict_id = self._find_conflict_video_id(
                        scheduled_items, entry.pillar, collision_slot.utc_datetime
                    )
                    warnings.append(
                        f"พบการชนของ pillar '{entry.pillar}' ภายใน 24 ชม. ระหว่าง {entry.video_id} และ {conflict_id}"
                    )

                    scheduled_items.append(
                        ScheduleEntry(
                            video_id=entry.video_id,
                            topic_title=entry.topic_title,
                            scheduled_datetime_utc=collision_slot.utc_datetime,
                            scheduled_datetime_local=collision_slot.local_datetime,
                            publish_status="collision",
                            pillar=entry.pillar,
                            content_type=entry.content_type,
                            priority_score=entry.priority_score,
                            reason=collision_slot.reason,
                            collision_with=conflict_id,
                            overflow_reason=None,
                            auto_publish_ready=False,
                        )
                    )
                else:
                    # Overflow case
                    overflow_reason = "ไม่มี slot ที่ว่างในสัปดาห์ตามลำดับความสำคัญและข้อจำกัด"
                    warnings.append(
                        f"วิดีโอ {entry.video_id} ไม่สามารถจัดตารางได้ ({overflow_reason})"
                    )
                    scheduled_items.append(
                        ScheduleEntry(
                            video_id=entry.video_id,
                            topic_title=entry.topic_title,
                            scheduled_datetime_utc=None,
                            scheduled_datetime_local=None,
                            publish_status="overflow",
                            pillar=entry.pillar,
                            content_type=entry.content_type,
                            priority_score=entry.priority_score,
                            reason="พิจารณาย้ายไปสัปดาห์ถัดไปหรือปรับข้อจำกัด",
                            collision_with=None,
                            overflow_reason=overflow_reason,
                            auto_publish_ready=False,
                        )
                    )

        meta = self._build_meta(scheduled_items)

        return SchedulingOutput(
            schedule_plan=scheduled_items,
            meta=meta,
            warnings=warnings,
        )

    # ------------------------------------------------------------------
    # Slot selection helpers
    # ------------------------------------------------------------------
    def _find_slot(
        self,
        entry: ContentCalendarEntry,
        constraints: ScheduleConstraints,
        analytics: AudienceAnalytics,
        base_monday: date,
        week_usage: dict[int, dict[str, int]],
        day_usage: dict[date, int],
        scheduled_slots: list[tuple[str, datetime]],
        timezone_info: ZoneInfo,
    ) -> CandidateSlot | None:
        """Find valid slot that respects all constraints."""

        return self._find_available_slot(
            entry,
            constraints,
            analytics,
            base_monday,
            week_usage,
            day_usage,
            scheduled_slots,
            timezone_info,
            max_weeks_to_check=6,
            check_pillar_collision=constraints.avoid_duplicate_pillar_in_24hr,
        )

    def _find_collision_slot(
        self,
        entry: ContentCalendarEntry,
        constraints: ScheduleConstraints,
        analytics: AudienceAnalytics,
        base_monday: date,
        week_usage: dict[int, dict[str, int]],
        day_usage: dict[date, int],
        scheduled_slots: list[tuple[str, datetime]],
        timezone_info: ZoneInfo,
    ) -> CandidateSlot | None:
        """Find slot allowing collision if no clean slot found."""

        return self._find_available_slot(
            entry,
            constraints,
            analytics,
            base_monday,
            week_usage,
            day_usage,
            scheduled_slots,
            timezone_info,
            max_weeks_to_check=4,
            check_pillar_collision=False,
        )

    def _find_available_slot(
        self,
        entry: ContentCalendarEntry,
        constraints: ScheduleConstraints,
        analytics: AudienceAnalytics,
        base_monday: date,
        week_usage: dict[int, dict[str, int]],
        day_usage: dict[date, int],
        scheduled_slots: list[tuple[str, datetime]],
        timezone_info: ZoneInfo,
        *,
        max_weeks_to_check: int,
        check_pillar_collision: bool,
    ) -> CandidateSlot | None:
        """Common logic for locating an available slot."""

        start_week_index = entry.week_index
        candidate_generator = self._candidate_slots(
            entry,
            analytics,
            base_monday,
            start_week_index,
            max_weeks_to_check,
            timezone_info,
        )

        for candidate in candidate_generator:
            if not self._check_week_capacity(
                week_usage[candidate.week_index], entry.content_type, constraints
            ):
                continue

            if (
                day_usage[candidate.local_datetime.date()]
                >= constraints.max_videos_per_day
            ):
                continue

            if constraints.is_forbidden(candidate.utc_datetime):
                continue

            if check_pillar_collision and self._has_pillar_collision(
                entry.pillar, candidate.utc_datetime, scheduled_slots
            ):
                continue

            return candidate

        return None

    def _candidate_slots(
        self,
        entry: ContentCalendarEntry,
        analytics: AudienceAnalytics,
        base_monday: date,
        start_week_index: int,
        max_weeks_to_check: int,
        timezone_info: ZoneInfo,
    ) -> Iterable[CandidateSlot]:
        """Yield candidate slots ordered by preference."""

        top_times = [self._parse_time(ts) for ts in analytics.top_time_slots_utc]
        avoid_times = {
            self._parse_time(ts) for ts in analytics.lowest_traffic_slots_utc
        }
        day_order = self._build_day_order(analytics.recent_best_days)

        for week_offset in range(max_weeks_to_check):
            week_index = start_week_index + week_offset
            week_start = base_monday + timedelta(weeks=week_index - 1)

            for day_idx in day_order:
                candidate_date = week_start + timedelta(days=day_idx)

                for slot_time in top_times:
                    if slot_time in avoid_times:
                        continue

                    local_dt = datetime.combine(
                        candidate_date, slot_time, timezone_info
                    )
                    utc_dt = local_dt.astimezone(UTC)
                    reason = self._build_reason(
                        candidate_date, slot_time, analytics, week_offset
                    )

                    yield CandidateSlot(
                        week_index=week_index,
                        local_datetime=local_dt,
                        utc_datetime=utc_dt,
                        reason=reason,
                    )

                # fallback slot at 19:00 local if no top slot used
                fallback_local = time(19, 0)
                if (
                    fallback_local not in top_times
                    and fallback_local not in avoid_times
                ):
                    local_dt = datetime.combine(
                        candidate_date, fallback_local, timezone_info
                    )
                    utc_dt = local_dt.astimezone(UTC)
                    reason = f"ใช้เวลา fallback 19:00 เพราะ slot prime เต็มในวัน {candidate_date.strftime('%A')}"
                    yield CandidateSlot(
                        week_index=week_index,
                        local_datetime=local_dt,
                        utc_datetime=utc_dt,
                        reason=reason,
                    )

    # ------------------------------------------------------------------
    # Helper utilities
    # ------------------------------------------------------------------
    def _determine_base_monday(
        self,
        input_data: SchedulingInput,
        timezone_info: ZoneInfo,
    ) -> date:
        """Determine base Monday date for W1."""

        if input_data.constraints.planning_start_date:
            return input_data.constraints.planning_start_date

        parsed_start_dates = [
            start for start, _ in input_data.constraints.forbidden_intervals_utc
        ]

        if parsed_start_dates:
            earliest_start = min(parsed_start_dates)
            earliest_monday = (
                earliest_start - timedelta(days=earliest_start.weekday())
            ).date()
            min_week_index = min(
                entry.week_index for entry in input_data.content_calendar
            )
            base = earliest_monday - timedelta(weeks=min_week_index - 1)
            return base

        raise ValueError(
            "planning_start_date หรือ forbidden_times ต้องถูกระบุเพื่อกำหนดสัปดาห์ตั้งต้น"
        )

    def _check_week_capacity(
        self,
        usage: dict[str, int],
        content_type: str,
        constraints: ScheduleConstraints,
    ) -> bool:
        limits = {
            "longform": constraints.max_longform_per_week,
            "shorts": constraints.max_shorts_per_week,
            "live": constraints.max_live_per_week,
            "audio": constraints.max_audio_per_week,
        }

        limit = limits.get(content_type)
        if limit is None:
            return True

        return usage[content_type] < limit

    def _has_pillar_collision(
        self,
        pillar: str,
        candidate_utc: datetime,
        scheduled_slots: list[tuple[str, datetime]],
    ) -> bool:
        twenty_four_hours = timedelta(hours=24)
        for scheduled_pillar, scheduled_time in scheduled_slots:
            if scheduled_pillar != pillar:
                continue
            if (
                abs((scheduled_time - candidate_utc).total_seconds())
                < twenty_four_hours.total_seconds()
            ):
                return True
        return False

    def _find_conflict_video_id(
        self,
        scheduled_items: list[ScheduleEntry],
        pillar: str,
        candidate_utc: datetime,
    ) -> str | None:
        twenty_four_hours = timedelta(hours=24)
        for item in scheduled_items:
            if item.pillar != pillar:
                continue
            if not item.scheduled_datetime_utc:
                continue
            if (
                abs((item.scheduled_datetime_utc - candidate_utc).total_seconds())
                < twenty_four_hours.total_seconds()
            ):
                return item.video_id
        return None

    def _build_meta(self, schedule_plan: list[ScheduleEntry]) -> ScheduleMeta:
        total = len(schedule_plan)
        scheduled_count = sum(
            1 for item in schedule_plan if item.publish_status == "scheduled"
        )
        collision_count = sum(
            1 for item in schedule_plan if item.publish_status == "collision"
        )
        overflow_count = sum(
            1 for item in schedule_plan if item.publish_status == "overflow"
        )
        pending_count = sum(
            1 for item in schedule_plan if item.publish_status == "pending"
        )

        pillar_distribution: dict[str, int] = defaultdict(int)
        for item in schedule_plan:
            if item.publish_status in {"scheduled", "collision"}:
                pillar_distribution[item.pillar] += 1

        self_check = SelfCheck(
            no_collision=collision_count == 0,
            no_overflow=overflow_count == 0,
            all_ready_have_slot=self._check_all_ready_have_slot(schedule_plan),
        )

        return ScheduleMeta(
            total_videos=total,
            scheduled_count=scheduled_count,
            collision_count=collision_count,
            overflow_count=overflow_count,
            pending_count=pending_count,
            pillar_distribution=dict(pillar_distribution),
            self_check=self_check,
        )

    def _check_all_ready_have_slot(self, schedule_plan: list[ScheduleEntry]) -> bool:
        return not any(item.publish_status == "overflow" for item in schedule_plan)

    def _build_day_order(self, recent_best_days: list[str]) -> list[int]:
        day_map = {
            "Monday": 0,
            "Tuesday": 1,
            "Wednesday": 2,
            "Thursday": 3,
            "Friday": 4,
            "Saturday": 5,
            "Sunday": 6,
        }
        preferred_days: set[int] = set()
        for name in recent_best_days:
            idx = day_map.get(name)
            if idx is not None:
                preferred_days.add(idx)

        ordered_best = sorted(preferred_days)
        remaining = [idx for idx in range(7) if idx not in preferred_days]
        return ordered_best + remaining

    def _build_reason(
        self,
        candidate_date: date,
        slot_time: time,
        analytics: AudienceAnalytics,
        week_offset: int,
    ) -> str:
        local_day = candidate_date.strftime("%A")
        slot_label = slot_time.strftime("%H:%M")
        week_desc = (
            "ตามสัปดาห์แนะนำ" if week_offset == 0 else f"ขยับไปสัปดาห์ที่ {week_offset + 1}"
        )
        if slot_label in analytics.top_time_slots_utc:
            return f"เลือก slot prime time ({slot_label}) วัน {local_day}, {week_desc}"
        return f"เลือก slot {slot_label} วัน {local_day} ({week_desc})"

    @staticmethod
    def _parse_time(value: str) -> time:
        hour, minute = value.split(":")
        return time(int(hour), int(minute))
