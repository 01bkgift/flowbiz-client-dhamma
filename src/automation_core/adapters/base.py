from __future__ import annotations

from typing import Any, Protocol, TypedDict

AdapterTarget = str


class AdapterError(Exception):
    def __init__(
        self, *, code: str, message: str, detail: object | None = None
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.detail = detail


class AdapterPreview(TypedDict):
    target: str
    platform: str
    mode: str
    actions: list[dict[str, Any]]
    errors: list[dict[str, Any]]


class AdapterProtocol(Protocol):
    def target(self) -> AdapterTarget:
        """Return the adapter target string."""

    def validate(self, publish_request: dict[str, Any]) -> None:
        """Validate publish_request for this adapter or raise AdapterError."""

    def build_preview(self, publish_request: dict[str, Any]) -> AdapterPreview:
        """Build a deterministic preview without mutating publish_request."""
