from __future__ import annotations

from .base import AdapterError, AdapterProtocol
from .targets import ALLOWED_TARGETS_V0


class AdapterRegistry:
    def __init__(self) -> None:
        self._adapters: dict[str, AdapterProtocol] = {}

    def register(self, adapter: AdapterProtocol) -> None:
        target = adapter.target()
        if not isinstance(target, str) or not target.strip():
            raise AdapterError(
                code="invalid_target",
                message="invalid_target: target must be a non-empty string",
            )
        if target not in ALLOWED_TARGETS_V0:
            raise AdapterError(
                code="disallowed_target",
                message=f"disallowed_target: target={target}",
            )
        if target in self._adapters:
            raise AdapterError(
                code="duplicate_target",
                message=f"duplicate_target: target={target}",
            )
        self._adapters[target] = adapter

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
    return AdapterRegistry()
