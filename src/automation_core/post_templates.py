"""
Deterministic post template rendering from pipeline artifacts and env params.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from automation_core.params import PIPELINE_PARAMS_ENV

PIPELINE_DISABLED_MESSAGE = "Pipeline disabled by PIPELINE_ENABLED=false"
REPO_ROOT = Path(__file__).resolve().parents[2]

ALLOWED_PLACEHOLDERS = {
    "run_id",
    "title",
    "hook",
    "summary",
    "cta",
    "hashtags",
    "lang",
    "platform",
    "source",
}
CONTENT_FIELDS = ("title", "hook", "summary", "cta", "hashtags", "lang", "platform")
ENV_SOURCE = f"env:{PIPELINE_PARAMS_ENV}"
PLACEHOLDER_RE = re.compile(r"\{\{([^}]*)\}\}")


def parse_pipeline_enabled(env_value: str | None) -> bool:
    if env_value is None:
        return True
    return env_value.strip().lower() not in ("false", "0", "no", "off", "disabled")


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _utc_iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _normalize_line_endings(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _normalize_hashtags(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        items = [str(item).strip() for item in value]
        items = [item for item in items if item]
        return " ".join(sorted(items))
    return " ".join(sorted(str(value).split()))


def _coerce_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _validate_run_id(run_id: str) -> str:
    if not isinstance(run_id, str) or not run_id.strip():
        raise ValueError("run_id is required")
    path = Path(run_id)
    if path.is_absolute() or path.drive or path.root:
        raise ValueError("run_id must be a relative path segment")
    if len(path.parts) != 1:
        raise ValueError("run_id must not contain path separators")
    if any(part in (".", "..") for part in path.parts):
        raise ValueError("run_id must not contain '.' or '..'")
    return run_id


def _validate_relative_path(value: str, field_name: str) -> str:
    path = Path(value)
    if path.is_absolute() or path.drive or path.root:
        raise ValueError(f"{field_name} must be relative")
    if any(part == ".." for part in path.parts):
        raise ValueError(f"{field_name} must not contain '..'")
    return value


def _relative_path(base_dir: Path, path: Path, field_name: str) -> str:
    try:
        rel = path.relative_to(base_dir)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be within base_dir") from exc
    return _validate_relative_path(rel.as_posix(), field_name)


def _read_json_file(path: Path) -> dict[str, Any] | None:
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


def _extract_env_params(payload: str) -> tuple[dict[str, str], set[str]]:
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ValueError("PIPELINE_PARAMS_JSON must be valid JSON") from exc
    if not isinstance(data, dict):
        raise ValueError("PIPELINE_PARAMS_JSON must be a JSON object")

    values: dict[str, str] = {}
    present: set[str] = set()
    for key in CONTENT_FIELDS:
        if key not in data:
            continue
        present.add(key)
        if key == "hashtags":
            values[key] = _normalize_hashtags(data[key])
        else:
            values[key] = _coerce_text(data[key])
    return values, present


def _extract_metadata_fields(data: dict[str, Any]) -> tuple[dict[str, str], set[str]]:
    values: dict[str, str] = {}
    present: set[str] = set()

    if "title" in data:
        values["title"] = _coerce_text(data["title"])
        present.add("title")

    summary_value = None
    description = data.get("description")
    if isinstance(description, str) and description.strip():
        summary_value = description
    elif description is not None and not isinstance(description, str):
        summary_value = _coerce_text(description)
    else:
        title_value = data.get("title")
        if isinstance(title_value, str) and title_value.strip():
            summary_value = title_value
        elif title_value is not None and not isinstance(title_value, str):
            summary_value = _coerce_text(title_value)

    if summary_value is not None:
        values["summary"] = summary_value
        present.add("summary")

    if "hashtags" in data:
        values["hashtags"] = _normalize_hashtags(data["hashtags"])
        present.add("hashtags")
    elif "tags" in data:
        values["hashtags"] = _normalize_hashtags(data["tags"])
        present.add("hashtags")

    if "language" in data:
        values["lang"] = _coerce_text(data["language"])
        present.add("lang")
    elif "lang" in data:
        values["lang"] = _coerce_text(data["lang"])
        present.add("lang")

    if "platform" in data:
        values["platform"] = _coerce_text(data["platform"])
        present.add("platform")

    return values, present


def _extract_video_summary_fields(
    data: dict[str, Any],
) -> tuple[dict[str, str], set[str]]:
    values: dict[str, str] = {}
    present: set[str] = set()

    for key in ("title", "hook", "summary", "cta", "lang", "platform"):
        if key in data:
            values[key] = _coerce_text(data[key])
            present.add(key)

    if "hashtags" in data:
        values["hashtags"] = _normalize_hashtags(data["hashtags"])
        present.add("hashtags")
    elif "tags" in data:
        values["hashtags"] = _normalize_hashtags(data["tags"])
        present.add("hashtags")

    return values, present


def _apply_source(
    *,
    values: dict[str, str],
    assigned: set[str],
    source_values: dict[str, str],
    present: set[str],
    source_label: str,
    sources: list[str],
) -> None:
    used = False
    for key in sorted(present):
        if key in assigned:
            continue
        values[key] = source_values.get(key, "")
        assigned.add(key)
        used = True
    if used:
        sources.append(source_label)


def _build_placeholder_values(
    run_id: str,
    *,
    base_dir: Path,
    pipeline_params_json: str | None = None,
) -> tuple[dict[str, str], list[str]]:
    run_id = _validate_run_id(run_id)
    values = {**dict.fromkeys(CONTENT_FIELDS, "")}
    assigned: set[str] = set()
    sources: list[str] = []

    env_payload = (
        pipeline_params_json
        if pipeline_params_json is not None
        else os.environ.get(PIPELINE_PARAMS_ENV)
    )
    if env_payload is not None and env_payload.strip():
        env_values, env_present = _extract_env_params(env_payload)
        _apply_source(
            values=values,
            assigned=assigned,
            source_values=env_values,
            present=env_present,
            source_label=ENV_SOURCE,
            sources=sources,
        )

    if any(field not in assigned for field in CONTENT_FIELDS):
        metadata_path = base_dir / "output" / run_id / "metadata.json"
        metadata = _read_json_file(metadata_path)
        if metadata is not None:
            meta_values, meta_present = _extract_metadata_fields(metadata)
            _apply_source(
                values=values,
                assigned=assigned,
                source_values=meta_values,
                present=meta_present,
                source_label=_relative_path(base_dir, metadata_path, "inputs.sources"),
                sources=sources,
            )

    if any(field not in assigned for field in CONTENT_FIELDS):
        video_summary_path = (
            base_dir / "output" / run_id / "artifacts" / "video_render_summary.json"
        )
        video_summary = _read_json_file(video_summary_path)
        if video_summary is not None:
            video_values, video_present = _extract_video_summary_fields(video_summary)
            _apply_source(
                values=values,
                assigned=assigned,
                source_values=video_values,
                present=video_present,
                source_label=_relative_path(
                    base_dir, video_summary_path, "inputs.sources"
                ),
                sources=sources,
            )

    values["run_id"] = run_id
    values["source"] = ""
    return values, sources


def load_template(
    template_name: str, *, base_dir: Path = REPO_ROOT
) -> tuple[Path, str]:
    if template_name not in ("short", "long"):
        raise ValueError("template_name must be 'short' or 'long'")
    template_path = base_dir / "templates" / "post" / f"{template_name}.md"
    text = template_path.read_text(encoding="utf-8")
    return template_path, text


def render_template(template_text: str, values: Mapping[str, str]) -> str:
    def _replace(match: re.Match[str]) -> str:
        raw_name = match.group(1)
        name = raw_name.strip()
        if name not in ALLOWED_PLACEHOLDERS:
            raise ValueError(f"Unknown placeholder '{name}'")
        return values.get(name, "")

    rendered = PLACEHOLDER_RE.sub(_replace, template_text)
    return _normalize_line_endings(rendered)


def render_post_templates(
    run_id: str,
    *,
    base_dir: Path = REPO_ROOT,
    pipeline_params_json: str | None = None,
) -> dict[str, Any]:
    values, sources = _build_placeholder_values(
        run_id,
        base_dir=base_dir,
        pipeline_params_json=pipeline_params_json,
    )

    short_path, short_template = load_template("short", base_dir=base_dir)
    long_path, long_template = load_template("long", base_dir=base_dir)

    short_text = render_template(short_template, values)
    long_text = render_template(long_template, values)

    template_short = _relative_path(base_dir, short_path, "inputs.template_short")
    template_long = _relative_path(base_dir, long_path, "inputs.template_long")

    return {
        "run_id": values["run_id"],
        "short": short_text,
        "long": long_text,
        "lang": values.get("lang", ""),
        "platform": values.get("platform", ""),
        "template_short": template_short,
        "template_long": template_long,
        "sources": sources,
    }


def build_post_content_summary(
    rendered: Mapping[str, Any],
    *,
    checked_at: datetime | None = None,
) -> dict[str, Any]:
    run_id = _validate_run_id(str(rendered.get("run_id", "")))
    template_short = _validate_relative_path(
        str(rendered.get("template_short", "")), "inputs.template_short"
    )
    template_long = _validate_relative_path(
        str(rendered.get("template_long", "")), "inputs.template_long"
    )
    sources = rendered.get("sources", [])
    if not isinstance(sources, list):
        raise ValueError("inputs.sources must be a list")
    for source in sources:
        if source == ENV_SOURCE:
            continue
        _validate_relative_path(str(source), "inputs.sources")

    checked_at_value = checked_at or _utc_now()
    if checked_at_value.tzinfo is None:
        checked_at_value = checked_at_value.replace(tzinfo=UTC)

    return {
        "schema_version": "v1",
        "engine": "post_templates",
        "run_id": run_id,
        "checked_at": _utc_iso(checked_at_value),
        "inputs": {
            "lang": _coerce_text(rendered.get("lang", "")),
            "platform": _coerce_text(rendered.get("platform", "")),
            "template_short": template_short,
            "template_long": template_long,
            "sources": list(sources),
        },
        "outputs": {
            "short": _coerce_text(rendered.get("short", "")),
            "long": _coerce_text(rendered.get("long", "")),
        },
    }


def write_post_content_summary(
    run_id: str, summary: Mapping[str, Any], *, base_dir: Path = REPO_ROOT
) -> Path:
    run_id = _validate_run_id(run_id)
    output_path = (
        base_dir / "output" / run_id / "artifacts" / "post_content_summary.json"
    )

    if not parse_pipeline_enabled(os.environ.get("PIPELINE_ENABLED")):
        return output_path

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return output_path


def generate_post_content_summary(
    run_id: str,
    *,
    base_dir: Path = REPO_ROOT,
    pipeline_params_json: str | None = None,
    checked_at: datetime | None = None,
) -> tuple[dict[str, Any], Path]:
    rendered = render_post_templates(
        run_id,
        base_dir=base_dir,
        pipeline_params_json=pipeline_params_json,
    )
    summary = build_post_content_summary(rendered, checked_at=checked_at)
    output_path = write_post_content_summary(run_id, summary, base_dir=base_dir)
    return summary, output_path


def cli_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Render post templates and write post_content_summary.json."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    render_parser = subparsers.add_parser("render", help="Render post templates")
    render_parser.add_argument("--run-id", required=True, help="Run identifier")

    args = parser.parse_args(argv)

    if args.command != "render":
        print("Error: unknown command", file=sys.stderr)
        return 1

    try:
        if not parse_pipeline_enabled(os.environ.get("PIPELINE_ENABLED")):
            print(PIPELINE_DISABLED_MESSAGE)
            return 0
        _, output_path = generate_post_content_summary(args.run_id, base_dir=REPO_ROOT)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Post content summary: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(cli_main())
