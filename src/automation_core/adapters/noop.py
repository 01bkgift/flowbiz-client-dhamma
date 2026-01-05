from __future__ import annotations

from typing import Any

from .base import AdapterPreview
from .preview import PUBLISH_REASON, build_bounded_preview


class NoopAdapter:
    def target(self) -> str:
        return "youtube_community"

    def validate(self, publish_request: dict[str, Any]) -> None:
        return None

    def build_preview(self, publish_request: dict[str, Any]) -> AdapterPreview:
        short_text = publish_request["request"]["content_short"]
        long_text = publish_request["request"]["content_long"]
        return {
            "target": publish_request["inputs"]["target"],
            "platform": publish_request["inputs"]["platform"],
            "mode": "dry_run",
            "actions": [
                {
                    "type": "print",
                    "label": "short",
                    "bytes": len(short_text.encode("utf-8")),
                    "preview": build_bounded_preview(short_text),
                },
                {
                    "type": "print",
                    "label": "long",
                    "bytes": len(long_text.encode("utf-8")),
                    "preview": build_bounded_preview(long_text),
                },
                {"type": "noop", "label": "publish", "reason": PUBLISH_REASON},
            ],
            "errors": [],
        }
