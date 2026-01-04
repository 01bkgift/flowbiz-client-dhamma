from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Protocol


class DispatchAdapter(Protocol):
    """สัญญา adapter สำหรับวางแผน actions แบบ audit-only"""

    name: str

    def supports(self, target: str, platform: str) -> bool:
        """คืน True เมื่อ adapter รองรับ (target, platform) ที่ระบุ."""

    def build_actions(
        self,
        *,
        short_bytes: int,
        long_bytes: int,
        publish_reason: str,
        target: str,
    ) -> list[dict[str, Any]]:
        """สร้างรายการ actions ตามสัญญาเดียวกันทุก adapter.

        ต้องคืน list ของ dict โดยมีโครงสร้างตามนี้:
        - action print short/long: {"type": "print", "label": ..., "bytes": int}
        - action publish: {"type": "noop", "label": "publish", "reason": str}

        ค่า bytes ที่ติดลบต้องถูก clamp เป็น 0.
        """


class PrintPublishAdapter(ABC):
    """ฐานร่วมสำหรับ adapter ที่ต้องการ actions แบบ print + publish."""

    name: str

    @abstractmethod
    def supports(self, target: str, platform: str) -> bool:
        """คืน True เมื่อ adapter รองรับ (target, platform) ที่ระบุ."""

    def build_actions(
        self,
        *,
        short_bytes: int,
        long_bytes: int,
        publish_reason: str,
        target: str,
    ) -> list[dict[str, Any]]:
        short_b = max(0, short_bytes)
        long_b = max(0, long_bytes)
        return [
            {
                "type": "print",
                "label": "short",
                "bytes": short_b,
                "adapter": self.name,
                "target": target,
            },
            {
                "type": "print",
                "label": "long",
                "bytes": long_b,
                "adapter": self.name,
                "target": target,
            },
            {
                "type": "noop",
                "label": "publish",
                "reason": publish_reason,
                "adapter": self.name,
                "target": target,
            },
        ]
