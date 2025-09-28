"""Unit tests สำหรับ DataSyncAgent"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agents.data_sync import DataSyncAgent, DataSyncRequest, SyncData, SyncRule


def build_request(**overrides) -> DataSyncRequest:
    """สร้าง DataSyncRequest สำหรับใช้งานในเทสต์"""

    base = {
        "source_system": "YouTube Analytics",
        "target_system": "Google Drive",
        "sync_type": "copy",
        "data": SyncData(
            file_name="analytics_2025-09-27.csv",
            schema_version="v2.1",
            fields=["video_id", "title", "views", "ctr_pct", "retention_pct"],
            row_count=134,
        ),
        "rule": SyncRule(overwrite_if_exists=True, validate_schema=True),
    }
    base.update(overrides)
    return DataSyncRequest(**base)


def test_data_sync_agent_success():
    agent = DataSyncAgent()
    request = build_request()

    response = agent.run(request)

    assert response.data_sync_payload.status == "ready"
    assert response.data_sync_payload.field_mapping == request.data.fields
    assert response.errors == []
    assert response.warnings == []
    assert response.suggestions == []

    events = [log.event for log in response.data_sync_log]
    assert events[0] == "schema_validated"
    assert events[-1] == "file_copied"
    assert response.data_sync_log[0].status == "success"
    assert response.data_sync_log[-1].status == "success"


def test_data_sync_agent_missing_fields_error():
    agent = DataSyncAgent()
    request = build_request(
        data=SyncData(
            file_name="analytics_2025-09-27.csv",
            schema_version="v2.1",
            fields=["video_id", "title", "views"],
            row_count=50,
        )
    )

    response = agent.run(request)

    assert response.data_sync_payload.status == "error"
    assert response.errors, "ควรมี error เมื่อฟิลด์ขาด"
    assert any("ฟิลด์" in error for error in response.errors)
    assert any(log.status == "failed" for log in response.data_sync_log)


def test_data_sync_agent_extra_fields_warning():
    agent = DataSyncAgent()
    request = build_request(
        data=SyncData(
            file_name="analytics_extra.csv",
            schema_version="v2.1",
            fields=[
                "video_id",
                "title",
                "views",
                "ctr_pct",
                "retention_pct",
                "watch_time",
            ],
            row_count=200,
        )
    )

    response = agent.run(request)

    assert response.data_sync_payload.status == "warning"
    assert response.errors == []
    assert response.warnings
    assert any("ฟิลด์เกิน" in warning for warning in response.warnings)
    assert response.data_sync_log[-1].status == "warning"


def test_data_sync_agent_unknown_schema_error():
    agent = DataSyncAgent()
    request = build_request(
        data=SyncData(
            file_name="analytics_future.csv",
            schema_version="v3.0",
            fields=["video_id", "title", "views"],
            row_count=10,
        )
    )

    response = agent.run(request)

    assert response.data_sync_payload.status == "error"
    assert any("schema_version" in error for error in response.errors)
    assert response.data_sync_log[0].status == "failed"


def test_data_sync_agent_row_count_zero_error():
    agent = DataSyncAgent()
    request = build_request(
        data=SyncData(
            file_name="analytics_empty.csv",
            schema_version="v2.1",
            fields=["video_id", "title", "views", "ctr_pct", "retention_pct"],
            row_count=0,
        )
    )

    response = agent.run(request)

    assert response.data_sync_payload.status == "error"
    assert any("row_count" in error for error in response.errors)
    assert any(
        log.event == "row_count_checked" and log.status == "failed"
        for log in response.data_sync_log
    )


@pytest.mark.parametrize(
    "sync_type",
    ["copy", "sync", "migrate", "update", "merge"],
)
def test_data_sync_agent_supports_multiple_sync_types(sync_type: str):
    agent = DataSyncAgent()
    request = build_request(sync_type=sync_type)

    response = agent.run(request)

    assert response.data_sync_payload.sync_type == sync_type
