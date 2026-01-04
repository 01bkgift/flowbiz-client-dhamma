from __future__ import annotations

from .base import PrintPublishAdapter


class YoutubeCommunityAdapter(PrintPublishAdapter):
    name = "youtube_community"

    def supports(self, target: str, platform: str) -> bool:
        return target == "youtube_community" and platform == "youtube_community"
