"""Shared utilities for scheduling & publishing."""

from __future__ import annotations

from datetime import datetime

__all__ = ["parse_iso_datetime"]


def parse_iso_datetime(value: str) -> datetime:
    """Parse ISO 8601 strings while supporting trailing ``Z`` shorthand."""

    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)
