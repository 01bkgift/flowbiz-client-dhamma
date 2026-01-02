"""
โมดูลสำหรับเรนเดอร์เทมเพลตโพสต์แบบกำหนดผลลัพธ์ตายตัว (deterministic)
จากอาร์ติแฟกต์ที่ได้จาก pipeline และพารามิเตอร์ในตัวแปรสภาพแวดล้อม
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
    """
    แปลงค่าจากตัวแปรสภาพแวดล้อมที่ใช้ควบคุมการเปิด/ปิด pipeline ให้เป็นค่า boolean

    Args:
        env_value: ค่าจากตัวแปรสภาพแวดล้อม PIPELINE_ENABLED หรือ None
            ถ้าเป็น None จะถือว่า pipeline เปิดใช้งานอยู่

    Returns:
        bool: True ถ้า pipeline ถือว่าเปิดใช้งาน
              False ถ้าค่าเป็นหนึ่งใน ("false", "0", "no", "off", "disabled")
              (ไม่คำนึงถึงตัวพิมพ์ใหญ่/เล็ก และตัดช่องว่างรอบข้างแล้ว)
    """
    if env_value is None:
        return True
    return env_value.strip().lower() not in ("false", "0", "no", "off", "disabled")


def _utc_now() -> datetime:
    """
    คืนค่าวันเวลาปัจจุบันในเขตเวลา UTC

    Returns:
        datetime: วันเวลาปัจจุบันแบบ timezone-aware ในเขตเวลา UTC
    """
    return datetime.now(UTC)


def _utc_iso(value: datetime) -> str:
    """
    แปลงค่าวันเวลาเป็นรูปแบบ ISO 8601 ในเขตเวลา UTC

    Args:
        value: วันเวลาที่ต้องการแปลง

    Returns:
        str: สตริงวันเวลาในรูปแบบ ISO 8601 โดยแทนที่ +00:00 ด้วย Z
    """
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _normalize_line_endings(text: str) -> str:
    """
    ปรับรูปแบบ line endings ให้เป็น Unix-style (\\n) เท่านั้น

    Args:
        text: ข้อความที่ต้องการปรับ line endings

    Returns:
        str: ข้อความที่แปลง \\r\\n และ \\r เป็น \\n แล้ว
    """
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _normalize_hashtags(value: Any) -> str:
    """
    ปรับรูปแบบแฮชแท็กให้เป็นสตริงที่ตัดช่องว่างส่วนเกิน

    Args:
        value: แฮชแท็กในรูปแบบ list, str หรือ None

    Returns:
        str: สตริงแฮชแท็กที่จัดรูปแบบแล้ว
             ถ้า value เป็น None จะคืนค่าสตริงว่าง
             ถ้า value เป็น list จะแปลงเป็นสตริง trim และ sort แล้วคั่นด้วยช่องว่าง
             ถ้า value เป็น str จะแยกคำและคั่นด้วยช่องว่างเดียว (ไม่ sort)
    """
    if value is None:
        return ""
    if isinstance(value, list):
        items = [str(item).strip() for item in value]
        items = [item for item in items if item]
        return " ".join(sorted(items))
    return " ".join(str(value).split())


def _coerce_text(value: Any) -> str:
    """
    บังคับแปลงค่าเป็นสตริง หรือคืนค่าสตริงว่างถ้าเป็น None

    Args:
        value: ค่าที่ต้องการแปลงเป็นสตริง

    Returns:
        str: สตริงที่แปลงจาก value หรือสตริงว่างถ้า value เป็น None
    """
    if value is None:
        return ""
    return str(value)


def _validate_run_id(run_id: str) -> str:
    """
    ตรวจสอบและ validate run_id ให้เป็น path segment เดียวที่ปลอดภัย

    Args:
        run_id: run identifier ที่ต้องการตรวจสอบ

    Returns:
        str: run_id ที่ผ่านการตรวจสอบแล้ว

    Raises:
        ValueError: ถ้า run_id ไม่ถูกต้อง เช่น เป็นสตริงว่าง, เป็น absolute path,
                   มี path separators, หรือมี '.' หรือ '..'
    """
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
    """
    ตรวจสอบว่า path เป็น relative path ที่ปลอดภัย

    Args:
        value: path ที่ต้องการตรวจสอบ
        field_name: ชื่อฟิลด์สำหรับแสดงใน error message

    Returns:
        str: path ที่ผ่านการตรวจสอบแล้ว

    Raises:
        ValueError: ถ้า path เป็น absolute path หรือมี '..' ซึ่งไม่ปลอดภัย
    """
    path = Path(value)
    if path.is_absolute() or path.drive or path.root:
        raise ValueError(f"{field_name} must be relative")
    if any(part == ".." for part in path.parts):
        raise ValueError(f"{field_name} must not contain '..'")
    return value


def _relative_path(base_dir: Path, path: Path, field_name: str) -> str:
    """
    คำนวณ relative path จาก base_dir และตรวจสอบความปลอดภัย

    Args:
        base_dir: directory ฐานที่ใช้อ้างอิง
        path: path แบบ absolute ที่ต้องการแปลงเป็น relative
        field_name: ชื่อฟิลด์สำหรับแสดงใน error message

    Returns:
        str: relative path ในรูปแบบ POSIX (ใช้ / เป็น separator)

    Raises:
        ValueError: ถ้า path ไม่อยู่ภายใน base_dir หรือไม่ผ่านการตรวจสอบความปลอดภัย
    """
    try:
        rel = path.relative_to(base_dir)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be within base_dir") from exc
    return _validate_relative_path(rel.as_posix(), field_name)


def _read_json_file(path: Path) -> dict[str, Any] | None:
    """
    อ่านและแปลงไฟล์ JSON เป็น dictionary

    Args:
        path: path ของไฟล์ JSON ที่ต้องการอ่าน

    Returns:
        dict[str, Any] | None: dictionary จากไฟล์ JSON หรือ None ถ้าไฟล์ไม่พบ

    Raises:
        ValueError: ถ้าไฟล์มี JSON ที่ไม่ถูกต้อง หรือไม่ใช่ JSON object
    """
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
    """
    แยกค่าพารามิเตอร์จาก PIPELINE_PARAMS_JSON

    Args:
        payload: JSON string จากตัวแปรสภาพแวดล้อม PIPELINE_PARAMS_JSON

    Returns:
        tuple[dict[str, str], set[str]]: คู่ของ (values, present) โดย
            - values: dictionary ของค่าฟิลด์ที่แปลงเป็นสตริงแล้ว
            - present: set ของชื่อฟิลด์ที่พบในข้อมูล

    Raises:
        ValueError: ถ้า payload ไม่ใช่ valid JSON หรือไม่ใช่ JSON object
    """
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
    """
    แยกค่าฟิลด์จากไฟล์ metadata.json

    Args:
        data: dictionary จากไฟล์ metadata.json

    Returns:
        tuple[dict[str, str], set[str]]: คู่ของ (values, present) โดย
            - values: dictionary ของค่าฟิลด์ที่แปลงเป็นสตริงแล้ว
            - present: set ของชื่อฟิลด์ที่พบในข้อมูล

    Note:
        ฟังก์ชันนี้จะแมป description -> summary, tags -> hashtags,
        language -> lang และดึงค่า title, platform
    """
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
    """
    แยกค่าฟิลด์จากไฟล์ video_render_summary.json

    Args:
        data: dictionary จากไฟล์ video_render_summary.json

    Returns:
        tuple[dict[str, str], set[str]]: คู่ของ (values, present) โดย
            - values: dictionary ของค่าฟิลด์ที่แปลงเป็นสตริงแล้ว
            - present: set ของชื่อฟิลด์ที่พบในข้อมูล

    Note:
        ฟังก์ชันนี้จะดึงค่า title, hook, summary, cta, lang, platform
        และแมป hashtags/tags -> hashtags
    """
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
    """
    นำค่าจาก source มาใส่ใน values สำหรับฟิลด์ที่ยังไม่ได้ assign และบันทึกชื่อ source

    Args:
        values: dictionary ของค่าฟิลด์ทั้งหมด (จะถูกแก้ไข in-place)
        assigned: set ของชื่อฟิลด์ที่ถูก assign แล้ว (จะถูกแก้ไข in-place)
        source_values: dictionary ของค่าจาก source นี้
        present: set ของชื่อฟิลด์ที่มีใน source นี้
        source_label: ชื่อของ source สำหรับบันทึก
        sources: list ของชื่อ source ที่ถูกใช้ (จะถูกแก้ไข in-place)

    Note:
        ฟังก์ชันนี้จะ assign ค่าเฉพาะฟิลด์ที่ยังไม่ได้ assign และจะเพิ่ม source_label
        ใน sources list เฉพาะเมื่อมีการใช้งานอย่างน้อยหนึ่งฟิลด์
    """
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
    """
    สร้าง dictionary ของค่า placeholder จากหลายแหล่งข้อมูลตามลำดับความสำคัญ

    Args:
        run_id: run identifier
        base_dir: directory ฐานของ repository
        pipeline_params_json: JSON string จาก PIPELINE_PARAMS_JSON (ถ้ามี)

    Returns:
        tuple[dict[str, str], list[str]]: คู่ของ (values, sources) โดย
            - values: dictionary ของค่า placeholder ทั้งหมด
            - sources: list ของ source ที่ถูกใช้ตามลำดับความสำคัญ

    Note:
        ลำดับความสำคัญของ source (จากสูงไปต่ำ):
        1. PIPELINE_PARAMS_JSON (env variable)
        2. metadata.json
        3. video_render_summary.json
    """
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
    """
    โหลดเทมเพลตโพสต์จากไฟล์

    Args:
        template_name: ชื่อเทมเพลต ('short' หรือ 'long')
        base_dir: directory ฐานของ repository

    Returns:
        tuple[Path, str]: คู่ของ (template_path, template_text)

    Raises:
        ValueError: ถ้า template_name ไม่ใช่ 'short' หรือ 'long'
        FileNotFoundError: ถ้าไฟล์เทมเพลตไม่พบ
    """
    if template_name not in ("short", "long"):
        raise ValueError("template_name must be 'short' or 'long'")
    template_path = base_dir / "templates" / "post" / f"{template_name}.md"
    text = template_path.read_text(encoding="utf-8")
    return template_path, text


def render_template(template_text: str, values: Mapping[str, str]) -> str:
    """
    เรนเดอร์เทมเพลตโดยแทนที่ placeholder ด้วยค่าจริง

    Args:
        template_text: ข้อความเทมเพลตที่มี placeholder ในรูปแบบ {{name}}
        values: dictionary ของค่าสำหรับแทนที่ placeholder

    Returns:
        str: ข้อความที่เรนเดอร์แล้วโดยแทนที่ placeholder และปรับ line endings

    Raises:
        ValueError: ถ้าพบ placeholder ที่ไม่รู้จัก (ไม่อยู่ใน ALLOWED_PLACEHOLDERS)
    """
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
    """
    เรนเดอร์เทมเพลตโพสต์ทั้ง short และ long

    Args:
        run_id: run identifier
        base_dir: directory ฐานของ repository
        pipeline_params_json: JSON string จาก PIPELINE_PARAMS_JSON (ถ้ามี)

    Returns:
        dict[str, Any]: dictionary ที่มี run_id, short, long, lang, platform,
                        template_short, template_long และ sources

    Raises:
        ValueError: ถ้า run_id ไม่ถูกต้อง หรือเทมเพลตมี placeholder ที่ไม่รู้จัก
    """
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
    """
    สร้าง summary artifact ในรูปแบบ JSON schema v1

    Args:
        rendered: dictionary จากการเรนเดอร์เทมเพลต (จาก render_post_templates)
        checked_at: timestamp สำหรับบันทึกเวลาที่ตรวจสอบ (ถ้าไม่ระบุจะใช้เวลาปัจจุบัน)

    Returns:
        dict[str, Any]: summary artifact ที่มี schema_version, engine, run_id,
                        checked_at, inputs และ outputs

    Raises:
        ValueError: ถ้าข้อมูลใน rendered ไม่ถูกต้องหรือไม่ผ่านการ validate
    """
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
    """
    เขียน summary artifact ลงไฟล์ post_content_summary.json

    Args:
        run_id: run identifier
        summary: summary artifact dictionary (จาก build_post_content_summary)
        base_dir: directory ฐานของ repository

    Returns:
        Path: path ของไฟล์ที่เขียน (หรือจะเขียนถ้า pipeline เปิดอยู่)

    Note:
        ถ้า PIPELINE_ENABLED=false จะไม่เขียนไฟล์ แต่จะคืนค่า path ตามปกติ
        (kill-switch enforcement)
    """
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
    """
    เรนเดอร์เทมเพลตและสร้างพร้อมเขียน summary artifact

    Args:
        run_id: run identifier
        base_dir: directory ฐานของ repository
        pipeline_params_json: JSON string จาก PIPELINE_PARAMS_JSON (ถ้ามี)
        checked_at: timestamp สำหรับบันทึกเวลาที่ตรวจสอบ

    Returns:
        tuple[dict[str, Any], Path]: คู่ของ (summary, output_path)
            - summary: summary artifact dictionary
            - output_path: path ของไฟล์ที่เขียน

    Note:
        เป็นฟังก์ชันหลักที่รวม render_post_templates, build_post_content_summary
        และ write_post_content_summary เข้าด้วยกัน
    """
    rendered = render_post_templates(
        run_id,
        base_dir=base_dir,
        pipeline_params_json=pipeline_params_json,
    )
    summary = build_post_content_summary(rendered, checked_at=checked_at)
    output_path = write_post_content_summary(run_id, summary, base_dir=base_dir)
    return summary, output_path


def cli_main(argv: list[str] | None = None) -> int:
    """
    CLI interface สำหรับเรนเดอร์เทมเพลตโพสต์

    Args:
        argv: command-line arguments (ถ้าไม่ระบุจะใช้ sys.argv)

    Returns:
        int: exit code (0 = success, 1 = error)

    Commands:
        render --run-id RUN_ID: เรนเดอร์เทมเพลตและสร้าง post_content_summary.json

    Note:
        - Kill-switch enforcement: ถ้า PIPELINE_ENABLED=false จะไม่เขียนไฟล์
        - พิมพ์ข้อความ "Pipeline disabled..." และคืนค่า 0 (ไม่ถือว่าเป็น error)
        - พิมพ์ path ของไฟล์ที่เขียนเมื่อสำเร็จ
    """
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
