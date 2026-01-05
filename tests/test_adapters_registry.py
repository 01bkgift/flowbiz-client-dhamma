from __future__ import annotations

from typing import Any

import pytest

from automation_core.adapters.base import AdapterError, AdapterPreview
from automation_core.adapters.registry import AdapterRegistry


class StubAdapter:
    def __init__(self, target: str) -> None:
        self._target = target

    def target(self) -> str:
        return self._target

    def validate(self, publish_request: dict[str, Any]) -> None:
        return None

    def build_preview(self, publish_request: dict[str, Any]) -> AdapterPreview:
        raise NotImplementedError


def test_registry_register_allowed_target():
    registry = AdapterRegistry()
    adapter = StubAdapter("youtube")
    registry.register(adapter)
    assert registry.get("youtube") is adapter


def test_registry_duplicate_registration_fails_deterministically():
    registry = AdapterRegistry()
    registry.register(StubAdapter("youtube"))
    with pytest.raises(AdapterError) as excinfo:
        registry.register(StubAdapter("youtube"))
    assert excinfo.value.code == "duplicate_target"
    assert excinfo.value.message == "duplicate_target: target=youtube"


def test_registry_list_targets_sorted():
    registry = AdapterRegistry()
    registry.register(StubAdapter("youtube"))
    registry.register(StubAdapter("facebook"))
    assert registry.list_targets() == ["facebook", "youtube"]


def test_registry_unknown_target_error_code_message_stable():
    registry = AdapterRegistry()
    with pytest.raises(AdapterError) as excinfo:
        registry.get("tiktok")
    assert excinfo.value.code == "unknown_target"
    assert excinfo.value.message == "unknown_target: target=tiktok"


def test_registry_register_rejects_empty_target():
    registry = AdapterRegistry()
    with pytest.raises(AdapterError) as excinfo:
        registry.register(StubAdapter(""))
    assert excinfo.value.code == "invalid_target"
    assert excinfo.value.message == "invalid_target: target must be a non-empty string"


def test_registry_register_rejects_whitespace_target():
    registry = AdapterRegistry()
    with pytest.raises(AdapterError) as excinfo:
        registry.register(StubAdapter(" youtube"))
    assert excinfo.value.code == "invalid_target"
    assert (
        excinfo.value.message
        == "invalid_target: target must not contain leading or trailing whitespace"
    )


def test_registry_register_rejects_disallowed_target():
    registry = AdapterRegistry()
    with pytest.raises(AdapterError) as excinfo:
        registry.register(StubAdapter("tiktok"))
    assert excinfo.value.code == "disallowed_target"
    assert excinfo.value.message == "disallowed_target: target=tiktok"


def test_registry_register_rejects_non_string_target():
    class NonStringTargetAdapter:
        def target(self) -> object:
            return 123

        def validate(self, publish_request: dict[str, Any]) -> None:
            return None

        def build_preview(self, publish_request: dict[str, Any]) -> AdapterPreview:
            raise NotImplementedError

    registry = AdapterRegistry()
    with pytest.raises(AdapterError) as excinfo:
        registry.register(NonStringTargetAdapter())
    assert excinfo.value.code == "invalid_target"
    assert excinfo.value.message == "invalid_target: target must be a non-empty string"
