"""DataSyncAgent - จัดการตรวจสอบและเตรียม payload สำหรับงานซิงก์ข้อมูล"""

from __future__ import annotations

from datetime import UTC, datetime

from automation_core.base_agent import BaseAgent

from .model import (
    DataSyncLogEntry,
    DataSyncPayload,
    DataSyncRequest,
    DataSyncResponse,
)


class DataSyncAgent(BaseAgent[DataSyncRequest, DataSyncResponse]):
    """Agent สำหรับประมวลผล data_sync_request และสร้าง payload พร้อม log"""

    def __init__(self) -> None:
        super().__init__(
            name="DataSyncAgent",
            version="1.0.0",
            description="ตรวจสอบ schema และเตรียม payload สำหรับงานซิงก์ข้อมูล",
        )

        # registry ของ schema เวอร์ชันต่างๆ และฟิลด์ที่คาดหวัง
        self.schema_registry: dict[str, list[str]] = {
            "v2.1": [
                "video_id",
                "title",
                "views",
                "ctr_pct",
                "retention_pct",
            ],
            "v2.0": [
                "video_id",
                "title",
                "views",
                "ctr_pct",
            ],
        }

    def run(self, input_data: DataSyncRequest) -> DataSyncResponse:
        timestamp = datetime.now(UTC)
        logs: list[DataSyncLogEntry] = []
        warnings: list[str] = []
        errors: list[str] = []
        suggestions: list[str] = []

        expected_fields = self.schema_registry.get(input_data.data.schema_version)

        # 1. ตรวจสอบ schema
        if input_data.rule.validate_schema:
            if expected_fields is None:
                errors.append(
                    f"ไม่รู้จัก schema_version '{input_data.data.schema_version}'"
                )
                logs.append(
                    DataSyncLogEntry(
                        timestamp=timestamp,
                        event="schema_validated",
                        status="failed",
                        message=(
                            f"schema_version {input_data.data.schema_version} ไม่อยู่ใน registry"
                        ),
                    )
                )
                suggestions.append("อัปเดต schema registry หรือใช้ schema_version ที่รองรับ")
            else:
                missing_fields = [
                    field
                    for field in expected_fields
                    if field not in input_data.data.fields
                ]
                extra_fields = [
                    field
                    for field in input_data.data.fields
                    if field not in expected_fields
                ]

                if missing_fields:
                    errors.append("พบฟิลด์ขาดหาย: " + ", ".join(sorted(missing_fields)))
                    suggestions.append("เติมข้อมูลฟิลด์ที่จำเป็นให้ตรงกับ schema ก่อนทำการซิงก์")
                    schema_status = "failed"
                    schema_message = "ฟิลด์ไม่ครบตาม schema: " + ", ".join(
                        sorted(missing_fields)
                    )
                else:
                    schema_status = "success"
                    schema_message = (
                        f"field mapping ตรง schema {input_data.data.schema_version}"
                    )

                logs.append(
                    DataSyncLogEntry(
                        timestamp=timestamp,
                        event="schema_validated",
                        status=schema_status,
                        message=schema_message,
                    )
                )

                if extra_fields:
                    warnings.append(
                        "พบฟิลด์เกินจาก schema: " + ", ".join(sorted(extra_fields))
                    )
                    suggestions.append(
                        "พิจารณาตรวจสอบฟิลด์ที่เกินก่อนการซิงก์หรืออัปเดต schema หากจำเป็น"
                    )

        # 2. ตรวจสอบ row_count
        if input_data.data.row_count <= 0:
            errors.append("row_count ต้องมากกว่า 0")
            logs.append(
                DataSyncLogEntry(
                    timestamp=timestamp,
                    event="row_count_checked",
                    status="failed",
                    message="จำนวนแถวเป็น 0 หรือค่าติดลบ",
                )
            )
            suggestions.append("ตรวจสอบขั้นตอนดึงข้อมูลหรือ filter ที่อาจทำให้ไม่มีข้อมูล")
        else:
            logs.append(
                DataSyncLogEntry(
                    timestamp=timestamp,
                    event="row_count_checked",
                    status="success",
                    message=f"row_count = {input_data.data.row_count}",
                )
            )

        # 3. ตรวจสอบ overwrite flag
        if input_data.rule.overwrite_if_exists:
            logs.append(
                DataSyncLogEntry(
                    timestamp=timestamp,
                    event="overwrite_flag",
                    status="pending",
                    message="ตั้งค่า overwrite_if_exists = true (ตรวจสอบไฟล์ปลายทางก่อนคัดลอก)",
                )
            )

        # 4. ตัดสินใจสถานะและ log ผลการคัดลอก
        if errors:
            final_status = "error"
            logs.append(
                DataSyncLogEntry(
                    timestamp=timestamp,
                    event="sync_aborted",
                    status="failed",
                    message="หยุดการซิงก์เนื่องจากพบข้อผิดพลาด",
                )
            )
        else:
            final_status = "warning" if warnings else "ready"
            logs.append(
                DataSyncLogEntry(
                    timestamp=timestamp,
                    event="file_copied",
                    status="warning" if warnings else "success",
                    message=(
                        f"copy {input_data.data.file_name} ไป {input_data.target_system} "
                        + ("พร้อมคำเตือน" if warnings else "สำเร็จ")
                    ),
                )
            )

        payload = DataSyncPayload(
            source_system=input_data.source_system,
            target_system=input_data.target_system,
            file_name=input_data.data.file_name,
            schema_version=input_data.data.schema_version,
            field_mapping=input_data.data.fields,
            row_count=input_data.data.row_count,
            sync_type=input_data.sync_type,
            rule=input_data.rule,
            status=final_status,
        )

        return DataSyncResponse(
            data_sync_payload=payload,
            data_sync_log=logs,
            suggestions=suggestions,
            warnings=warnings,
            errors=errors,
        )
