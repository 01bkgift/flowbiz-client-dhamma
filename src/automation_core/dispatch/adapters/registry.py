from __future__ import annotations

from .base import DispatchAdapter
from .youtube import YoutubeAdapter
from .youtube_community import YoutubeCommunityAdapter


class DispatchAdapterError(Exception):
    def __init__(self, *, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


_ADAPTERS: tuple[DispatchAdapter, ...] = (
    YoutubeAdapter(),
    YoutubeCommunityAdapter(),
)


def get_adapter(target: str, platform: str) -> DispatchAdapter:
    """คืน adapter แบบ deterministic จาก (target, platform)

    ตรวจสอบ adapter ตามลำดับใน _ADAPTERS และคืนตัวแรกที่รองรับ.

    Raises:
        DispatchAdapterError: code='unknown_target' เมื่อไม่พบ adapter ที่รองรับ
    """
    for adapter in _ADAPTERS:
        if adapter.supports(target, platform):
            return adapter
    raise DispatchAdapterError(
        code="unknown_target",
        message=f"unknown_target: target={target} platform={platform}",
    )
