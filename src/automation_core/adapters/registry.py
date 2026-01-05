from __future__ import annotations

from .base import AdapterError, AdapterProtocol
from .targets import ALLOWED_TARGETS_V0


class AdapterRegistry:
    def __init__(self) -> None:
        self._adapters: dict[str, AdapterProtocol] = {}

    def register(self, adapter: AdapterProtocol) -> None:
        target = adapter.target()
        if not isinstance(target, str):
            raise AdapterError(
                code="invalid_target",
                message="invalid_target: target must be a non-empty string",
            )
        normalized_target = target.strip()
        if not normalized_target:
            raise AdapterError(
                code="invalid_target",
                message="invalid_target: target must be a non-empty string",
            )
        if normalized_target != target:
            raise AdapterError(
                code="invalid_target",
                message=(
                    "invalid_target: target must not contain leading or trailing whitespace"
                ),
            )
        if normalized_target not in ALLOWED_TARGETS_V0:
            raise AdapterError(
                code="disallowed_target",
                message=f"disallowed_target: target={normalized_target}",
            )
        if normalized_target in self._adapters:
            raise AdapterError(
                code="duplicate_target",
                message=f"duplicate_target: target={normalized_target}",
            )
        self._adapters[normalized_target] = adapter

    def get(self, target: str) -> AdapterProtocol:
        adapter = self._adapters.get(target)
        if adapter is None:
            raise AdapterError(
                code="unknown_target",
                message=f"unknown_target: target={target}",
            )
        return adapter

    def list_targets(self) -> list[str]:
        return sorted(self._adapters.keys())


def get_default_registry() -> AdapterRegistry:
    """Return the default v0 adapter registry used for deterministic previews."""
    registry = AdapterRegistry()
    from .noop import NoopAdapter

    registry.register(NoopAdapter(target="youtube_community"))
    return registry
