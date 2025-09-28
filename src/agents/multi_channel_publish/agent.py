"""Implementation of the Multi-Channel Publish agent."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from automation_core.base_agent import BaseAgent

from .model import (
    ChannelPublishPayload,
    MultiChannelPublishInput,
    MultiChannelPublishLogEntry,
    MultiChannelPublishOutput,
    PublishRequest,
)


class MultiChannelPublishAgent(
    BaseAgent[MultiChannelPublishInput, MultiChannelPublishOutput]
):
    """Agent responsible for preparing multi-channel publish payloads."""

    SUPPORTED_CHANNELS = {"YouTube", "TikTok", "Facebook"}

    def __init__(self) -> None:
        super().__init__(
            name="MultiChannelPublishAgent",
            version="1.0.0",
            description="จัดระเบียบ payload สำหรับเผยแพร่คอนเทนต์หลายแพลตฟอร์ม",
        )

    def run(self, input_data: MultiChannelPublishInput) -> MultiChannelPublishOutput:
        request = input_data.publish_request
        timestamp = datetime.now(UTC)

        payloads: list[ChannelPublishPayload] = []
        logs: list[MultiChannelPublishLogEntry] = []
        warnings: list[str] = []
        errors: list[str] = []

        for channel in request.channels:
            if channel not in self.SUPPORTED_CHANNELS:
                message = f"ไม่รองรับช่องทาง '{channel}'"
                payloads.append(
                    ChannelPublishPayload(
                        channel=channel,
                        mapped_data={},
                        status="error",
                        suggestion=[
                            "ตรวจสอบการสะกดชื่อช่องทางหรือเพิ่มการรองรับในระบบ",
                        ],
                    )
                )
                errors.append(message)
                logs.append(
                    MultiChannelPublishLogEntry(
                        timestamp=timestamp,
                        event="mapping_failed",
                        channel=channel,
                        status="failed",
                        message=message,
                    )
                )
                continue

            mapped_data, suggestions, missing_fields = self._map_channel(
                channel, request
            )

            if missing_fields:
                status = "missing_data"
                message = f"{channel} payload missing fields: {', '.join(sorted(missing_fields))}"
                warnings.append(message)
                log_status = "warning"
                event = "mapping_missing_data"
            else:
                status = "ready"
                message = f"{channel} payload ready"
                log_status = "success"
                event = "mapping_success"

            payloads.append(
                ChannelPublishPayload(
                    channel=channel,
                    mapped_data=mapped_data,
                    status=status,
                    suggestion=suggestions,
                )
            )
            logs.append(
                MultiChannelPublishLogEntry(
                    timestamp=timestamp,
                    event=event,
                    channel=channel,
                    status=log_status,
                    message=message,
                )
            )

        return MultiChannelPublishOutput(
            multi_channel_publish_payload=payloads,
            multi_channel_publish_log=logs,
            warnings=warnings,
            errors=errors,
        )

    # ------------------------------------------------------------------
    # Mapping helpers
    # ------------------------------------------------------------------
    def _map_channel(
        self, channel: str, request: PublishRequest
    ) -> tuple[dict[str, Any], list[str], list[str]]:
        mapper = getattr(self, f"_map_{channel.lower()}", None)
        if mapper is None:
            return {}, ["ยังไม่มี logic สำหรับช่องทางนี้"], ["mapping_not_implemented"]
        return mapper(request)

    def _map_youtube(
        self, request: PublishRequest
    ) -> tuple[dict[str, Any], list[str], list[str]]:
        mapped = {
            "video": request.assets.video,
            "title": request.title,
            "description": request.description,
            "tags": request.tags,
            "thumbnail": request.assets.thumbnail,
            "schedule": request.schedule.get("YouTube"),
            "privacy": request.privacy.get("YouTube"),
        }
        required = {
            "video": "เพิ่มไฟล์วิดีโอหลัก (assets.video)",
            "title": "ระบุหัวข้อวิดีโอ",
            "description": "กรอกคำอธิบายวิดีโอ",
            "schedule": "ตั้งเวลาปล่อยวิดีโอใน schedule['YouTube']",
            "privacy": "กำหนด privacy สำหรับ YouTube",
            "thumbnail": "อัปโหลด thumbnail สำหรับ YouTube",
        }
        missing = [key for key, suggestion in required.items() if not mapped.get(key)]
        suggestions = [required[key] for key in missing]
        return mapped, suggestions, missing

    def _map_tiktok(
        self, request: PublishRequest
    ) -> tuple[dict[str, Any], list[str], list[str]]:
        extra = request.extra_setting.get("TikTok", {})
        mapped = {
            "video": request.assets.vertical_video,
            "caption": extra.get("caption"),
            "hashtag": extra.get("hashtag", []),
            "schedule": request.schedule.get("TikTok"),
            "privacy": request.privacy.get("TikTok"),
        }
        required = {
            "video": "เตรียมไฟล์วิดีโอแนวตั้งสำหรับ TikTok",
            "caption": "กำหนดคำบรรยาย (extra_setting['TikTok']['caption'])",
            "schedule": "ตั้งเวลาโพสต์ TikTok ใน schedule['TikTok']",
            "privacy": "กำหนด privacy สำหรับ TikTok",
        }
        missing = [key for key, suggestion in required.items() if not mapped.get(key)]
        suggestions = [required[key] for key in missing]
        return mapped, suggestions, missing

    def _map_facebook(
        self, request: PublishRequest
    ) -> tuple[dict[str, Any], list[str], list[str]]:
        extra = request.extra_setting.get("Facebook", {})
        mapped = {
            "video": request.assets.video,
            "post_message": extra.get("post_message", request.description),
            "thumbnail": request.assets.thumbnail,
            "schedule": request.schedule.get("Facebook"),
            "privacy": request.privacy.get("Facebook"),
        }
        required = {
            "video": "เพิ่มไฟล์วิดีโอหลัก (assets.video) สำหรับ Facebook",
            "post_message": "กำหนดข้อความโพสต์ใน extra_setting['Facebook']['post_message']",
            "schedule": "ตั้งเวลาโพสต์ Facebook ใน schedule['Facebook']",
            "privacy": "กำหนด privacy สำหรับ Facebook",
        }
        missing = [key for key, suggestion in required.items() if not mapped.get(key)]
        suggestions = [required[key] for key in missing]
        return mapped, suggestions, missing
