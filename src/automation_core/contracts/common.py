from __future__ import annotations

import hashlib
from pathlib import Path


def _validate_run_id(run_id: str) -> str:
    """Ensure run_id is a single relative path segment."""
    path = Path(run_id)
    if not run_id or path.is_absolute() or path.drive or path.root:
        raise ValueError("run_id must be a relative path segment")
    if len(path.parts) != 1 or any(part in (".", "..") for part in path.parts):
        raise ValueError("run_id must not contain path separators or traversal")
    return run_id


def _validate_relative_path(value: str, label: str, *, check_root: bool = True) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} is required")
    path = Path(value)
    root = path.root if check_root else ""
    if path.is_absolute() or path.drive or root or ".." in path.parts:
        raise ValueError(f"{label} must be relative without '..'")
    return value


def _artifact_rel_path(run_id: str, filename: str, *, validate: bool = True) -> str:
    if validate:
        run_id = _validate_run_id(run_id)
    return (Path("output") / run_id / "artifacts" / filename).as_posix()


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
