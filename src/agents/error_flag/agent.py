"""Implementation of the Error/Flag aggregation agent."""

from __future__ import annotations

from collections import Counter, defaultdict

from automation_core.base_agent import BaseAgent

from .model import (
    CriticalItem,
    ErrorFlagInput,
    ErrorFlagOutput,
    MetaSection,
    SelfCheck,
    WarningItem,
)

# ---------------------------------------------------------------------------
# Message libraries for known flags/warnings
# ---------------------------------------------------------------------------

_FLAG_LIBRARY: dict[str, tuple[str, str]] = {
    "mid_clip_drop": ("Retention ลดช่วงกลางคลิป", "ปรับ pacing, shorten ช่วงกลาง"),
    "low_comments": ("จำนวนคอมเมนต์ต่ำกว่าค่าเฉลี่ย", "เพิ่ม CTA กระตุ้นคอมเมนต์"),
    "underperform": (
        "ผลงานของคอนเทนต์ต่ำกว่าค่าเฉลี่ย",
        "ปรับ thumbnail/title หรือปรับ narrative",
    ),
    "schema_violation": (
        "ข้อมูลไม่ตรงตาม schema ที่กำหนด",
        "ตรวจสอบ pipeline data และแก้ schema",
    ),
    "no_slot": ("ไม่มี slot ว่างตามเงื่อนไข", "ปรับตารางหรือเพิ่ม slot ใหม่"),
    "OVERLAP": (
        "พบวิดีโอ pillar ซ้ำใน 24 ชม.",
        "เลื่อน publish slot หรือสลับวันเผยแพร่",
    ),
}

_WARNING_LIBRARY: dict[str, tuple[str, str]] = {
    "overflow_count > 0": (
        "มีวิดีโอรอ publish เกินโควต้าต่อวัน/สัปดาห์",
        "กระจาย schedule เพิ่มหรือเพิ่ม slot",
    ),
}

_CRITICAL_FLAGS = {"no_slot", "overlap"}


class ErrorFlagAgent(BaseAgent[ErrorFlagInput, ErrorFlagOutput]):
    """Agent รวม error/flag/warning จาก workflow."""

    def __init__(self) -> None:
        super().__init__(
            name="ErrorFlagAgent",
            version="1.0.0",
            description=(
                "รวบรวม ตรวจสอบ และสรุป error/flag/warning จากทุก agent ใน workflow"
            ),
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def run(self, input_data: ErrorFlagInput) -> ErrorFlagOutput:
        """Aggregate logs and produce summary output."""

        summary: list[str] = []
        critical_items: list[CriticalItem] = []
        warning_items: list[WarningItem] = []
        info_items: list[str] = []

        error_counter: Counter[str] = Counter()
        flag_counter: Counter[str] = Counter()
        warning_counter: Counter[str] = Counter()

        error_messages: dict[str, str] = {}
        flag_messages: dict[str, str] = {}
        warning_messages: dict[str, str] = {}

        unique_agents = {log.agent for log in input_data.agent_logs}

        # Collect per-agent flags for summary reporting
        flags_per_agent: dict[str, list[str]] = defaultdict(list)

        for log in input_data.agent_logs:
            # ------------------------------------------------------------------
            # Errors → critical severity
            # ------------------------------------------------------------------
            if log.error:
                error_counter[log.error.code] += 1
                error_messages[log.error.code] = log.error.message
                summary.append(f"{log.agent} {log.error.message} ({log.error.code})")
                critical_items.append(
                    CriticalItem(
                        agent=log.agent,
                        error_code=log.error.code,
                        message=log.error.message,
                        suggested_action=log.error.suggested_fix,
                    )
                )

            # ------------------------------------------------------------------
            # Flags → warning or critical severity depending on type
            # ------------------------------------------------------------------
            if log.flags:
                flags_per_agent[log.agent].extend(log.flags)

            for flag in log.flags:
                normalized = flag.lower()
                flag_counter[normalized] += 1
                message, action = _FLAG_LIBRARY.get(
                    flag,
                    (f"พบ flag '{flag}'", "ตรวจสอบรายละเอียด flag เพิ่มเติมกับทีมที่เกี่ยวข้อง"),
                )
                flag_messages[normalized] = message

                if normalized in _CRITICAL_FLAGS:
                    critical_items.append(
                        CriticalItem(
                            agent=log.agent,
                            error_code=flag,
                            message=message,
                            suggested_action=action,
                        )
                    )
                else:
                    warning_items.append(
                        WarningItem(
                            agent=log.agent,
                            flag=flag,
                            message=message,
                            suggested_action=action,
                        )
                    )

            # ------------------------------------------------------------------
            # Warnings → warning severity (info if explicitly tagged otherwise)
            # ------------------------------------------------------------------
            for warning in log.warnings:
                warning_counter[warning] += 1
                message, action = _WARNING_LIBRARY.get(
                    warning,
                    (
                        f"พบ warning '{warning}'",
                        "ตรวจสอบและจัดการ warning ตามความเหมาะสม",
                    ),
                )
                warning_messages[warning] = message
                warning_items.append(
                    WarningItem(
                        agent=log.agent,
                        warning=warning,
                        message=message,
                        suggested_action=action,
                    )
                )

        # Add summary entries for agents that only had flags (no error)
        for agent_name, agent_flags in flags_per_agent.items():
            if agent_flags:
                summary.append(f"{agent_name} flag {', '.join(agent_flags)}")

        if not summary:
            summary.append("ไม่พบ error/flag จาก agent logs รอบนี้")

        # Root cause detection (recurring issues >= 2 times)
        root_causes = _build_root_cause_messages(
            error_counter,
            error_messages,
            flag_counter,
            flag_messages,
            warning_counter,
            warning_messages,
        )

        if not root_causes:
            root_causes.append("ยังไม่พบ recurring error/flag จากข้อมูลรอบนี้")

        self_check = SelfCheck(
            all_sections_present=bool(
                summary and root_causes and (critical_items or warning_items)
            ),
            no_empty_fields=bool(summary and root_causes),
        )

        meta = MetaSection(
            total_error=sum(error_counter.values()),
            total_flag=sum(flag_counter.values()),
            total_warning=sum(warning_counter.values()),
            unique_agents=len(unique_agents),
            self_check=self_check,
        )

        return ErrorFlagOutput(
            summary=summary,
            critical=critical_items,
            warning=warning_items,
            info=info_items,
            root_cause=root_causes,
            meta=meta,
        )


def _build_root_cause_messages(
    error_counter: Counter[str],
    error_messages: dict[str, str],
    flag_counter: Counter[str],
    flag_messages: dict[str, str],
    warning_counter: Counter[str],
    warning_messages: dict[str, str],
) -> list[str]:
    """สร้างข้อความ root cause จากสถิติต่าง ๆ."""

    messages: list[str] = []

    for code, count in error_counter.items():
        if count >= 2:
            message = error_messages.get(code, code)
            messages.append(f"{message} พบ {count} ครั้ง")

    for flag, count in flag_counter.items():
        if count >= 2:
            message = flag_messages.get(flag, flag)
            messages.append(f"Flag '{flag}' ({message}) เกิดขึ้น {count} ครั้ง")

    for warning, count in warning_counter.items():
        if count >= 2:
            message = warning_messages.get(warning, warning)
            messages.append(f"Warning '{warning}' ({message}) เกิดขึ้น {count} ครั้ง")

    return messages


__all__ = ["ErrorFlagAgent"]
