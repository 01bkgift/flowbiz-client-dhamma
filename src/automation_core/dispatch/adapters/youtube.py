from __future__ import annotations

from .base import PrintPublishAdapter


class YoutubeAdapter(PrintPublishAdapter):
    name = "youtube"

    def supports(self, target: str, platform: str) -> bool:
        return target == "youtube" and platform == "youtube"
