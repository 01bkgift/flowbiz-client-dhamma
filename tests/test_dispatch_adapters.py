from __future__ import annotations

import pytest

from automation_core.dispatch.adapters.base import PrintPublishAdapter

from automation_core.dispatch.adapters.registry import DispatchAdapterError, get_adapter
from automation_core.dispatch.adapters.youtube import YoutubeAdapter
from automation_core.dispatch.adapters.youtube_community import YoutubeCommunityAdapter


@pytest.mark.parametrize(
    ("target_and_platform", "expected_name"),
    [
        ("youtube_community", "youtube_community"),
        ("youtube", "youtube"),
    ],
)
def test_registry_resolves_adapter(target_and_platform, expected_name):
    adapter = get_adapter(target_and_platform, target_and_platform)
    assert adapter.name == expected_name


def test_registry_unknown_target_raises_deterministic_error():
    with pytest.raises(DispatchAdapterError) as excinfo:
        get_adapter("line", "youtube_community")
    assert excinfo.value.code == "unknown_target"
    assert "unknown_target:" in excinfo.value.message


@pytest.mark.parametrize(
    ("adapter_class", "target_name"),
    [
        (YoutubeCommunityAdapter, "youtube_community"),
        (YoutubeAdapter, "youtube"),
    ],
)
def test_print_publish_adapter_build_actions_contract(adapter_class, target_name):
    adapter = adapter_class()
    actions = adapter.build_actions(
        short_bytes=5,
        long_bytes=7,
        publish_reason="dry_run default",
        target=target_name,
    )

    assert len(actions) == 3
    assert actions[0]["type"] == "print" and actions[0]["label"] == "short"
    assert actions[1]["type"] == "print" and actions[1]["label"] == "long"
    assert actions[2]["type"] == "noop" and actions[2]["label"] == "publish"

    assert actions[0]["bytes"] == 5
    assert actions[1]["bytes"] == 7
    assert actions[2]["reason"] == "dry_run default"

    assert actions[0]["adapter"] == target_name
    assert actions[0]["target"] == target_name


def test_print_publish_adapter_is_abstract():
    with pytest.raises(TypeError):
        PrintPublishAdapter()


def test_print_publish_adapter_requires_supports():
    class IncompleteAdapter(PrintPublishAdapter):
        name = "incomplete"

    with pytest.raises(TypeError):
        IncompleteAdapter()
