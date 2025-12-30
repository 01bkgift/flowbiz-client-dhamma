"""
โมดูลสำหรับสร้างไฟล์เสียง Voiceover แบบ deterministic พร้อม metadata

โมดูลนี้จัดการการแปลงข้อความเป็นเสียง (Text-to-Speech) โดยใช้ระบบ content-addressed naming
ที่สร้างชื่อไฟล์จาก SHA-256 hash ของข้อความเพื่อให้ผลลัพธ์เหมือนกันทุกครั้งที่ใช้ input เดียวกัน
รองรับ kill switch (PIPELINE_ENABLED) และสร้าง metadata JSON ที่มี schema คงที่
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import wave
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

PIPELINE_DISABLED_MESSAGE = "Pipeline disabled by PIPELINE_ENABLED=false"
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_VOICEOVER_DIR = REPO_ROOT / "data" / "voiceovers"
SHA_PREFIX_LENGTH = 12
WAV_SAMPLE_RATE = 16000
WAV_CHANNELS = 1
WAV_SAMPLE_WIDTH_BYTES = 2
NULL_TTS_DURATION_SECONDS = 1.0
_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")


class TTSEngine(Protocol):
    """
    Protocol สำหรับเอนจินแปลงข้อความเป็นเสียง (Text-to-Speech)

    คลาสนี้กำหนดสัญญาการทำงานขั้นต่ำที่เอนจิน TTS ต้องรองรับ
    ได้แก่ ชื่อเอนจิน และเมธอดสำหรับสังเคราะห์เสียงจากข้อความ
    แล้วบันทึกเป็นไฟล์เสียงรูปแบบ WAV
    """

    name: str

    def synthesize(self, text: str, output_path: Path) -> None:
        """
        สังเคราะห์เสียงจากข้อความและบันทึกเป็นไฟล์ WAV

        Args:
            text: ข้อความภาษาไทยหรือภาษาอื่นที่ต้องการแปลงเป็นเสียงพูด
            output_path: พาธไฟล์ปลายทางสำหรับบันทึกไฟล์เสียงรูปแบบ WAV
                ต้องเป็นไฟล์ที่สามารถเขียนทับได้ หากมีอยู่ก่อนแล้ว

        Returns:
            None: เมธอดนี้จะเขียนไฟล์ WAV ไปที่ output_path โดยไม่คืนค่า
        """


def parse_pipeline_enabled(env_value: str | None) -> bool:
    """
    แปลงค่าจากตัวแปรสภาพแวดล้อมเพื่อเช็คว่า PIPELINE_ENABLED เปิดอยู่หรือไม่

    Args:
        env_value: ค่าจากตัวแปรสภาพแวดล้อม PIPELINE_ENABLED ซึ่งอาจเป็น None
            หรือสตริง เช่น "true", "false", "0", "1"

    Returns:
        True หากไม่ได้กำหนดค่า (None) หรือค่าที่ไม่ใช่
        "false", "0", "no", "off", "disabled" (ไม่สนตัวพิมพ์เล็กใหญ่)
        และ False หากเป็นหนึ่งในค่าปิดเหล่านั้น
    """
    if env_value is None:
        return True
    return env_value.strip().lower() not in ("false", "0", "no", "off", "disabled")


def is_pipeline_enabled() -> bool:
    """
    ตรวจสอบสถานะการทำงานของ pipeline จากตัวแปรสภาพแวดล้อม PIPELINE_ENABLED

    ถ้าไม่ได้กำหนดตัวแปร PIPELINE_ENABLED จะถือว่า pipeline เปิดใช้งาน (ค่า True)

    Returns:
        ค่า True ถ้า pipeline ถูกเปิดใช้งาน
        ค่า False ถ้า pipeline ถูกปิด (เช่น PIPELINE_ENABLED เป็น false, 0, no, off, disabled)
    """
    return parse_pipeline_enabled(os.environ.get("PIPELINE_ENABLED"))


def _validate_identifier(value: str, field_name: str) -> str:
    """
    ตรวจสอบความถูกต้องของตัวระบุ (identifier) เพื่อป้องกัน path traversal และให้ filesystem-safe

    Args:
        value: สตริงที่ต้องการตรวจสอบ
        field_name: ชื่อฟิลด์สำหรับแสดงใน error message

    Returns:
        ค่า value ที่ผ่านการตรวจสอบแล้ว

    Raises:
        ValueError: ถ้า value ว่างเปล่า, เป็น '.' หรือ '..',
            มี path separator หรือไม่ตรงกับรูปแบบที่อนุญาต (ตัวอักษร ตัวเลข _ -)
    """
    if not value or not value.strip():
        raise ValueError(f"{field_name} is required")

    if value in {".", ".."}:
        raise ValueError(f"{field_name} must not be '.' or '..'")

    for sep in (os.sep, os.altsep):
        if sep and sep in value:
            raise ValueError(f"{field_name} must not contain path separators")

    if not _IDENTIFIER_RE.fullmatch(value):
        raise ValueError(
            f"{field_name} must be filesystem-safe (letters, digits, _, -)"
        )

    return value


def compute_input_sha256(script_text: str) -> str:
    """
    คำนวณค่าแฮช SHA-256 ของข้อความสคริปต์เพื่อใช้เป็นตัวระบุอินพุต

    Args:
        script_text: ข้อความสคริปต์ที่ต้องการคำนวณค่าแฮช

    Returns:
        สตริงค่าแฮช SHA-256 ในรูปแบบเลขฐานสิบหก (hex digest) ความยาว 64 ตัวอักษร

    Raises:
        TypeError: ถ้า script_text ไม่ใช่สตริง
    """
    if not isinstance(script_text, str):
        raise TypeError("script_text must be a string")
    return hashlib.sha256(script_text.encode("utf-8")).hexdigest()


def build_voiceover_paths(
    run_id: str, slug: str, input_sha256: str, base_dir: Path | None = None
) -> tuple[Path, Path]:
    """
    สร้าง path สำหรับไฟล์ WAV และ metadata JSON โดยใช้ content-addressed naming

    Args:
        run_id: ตัวระบุการรัน (run identifier) ที่เป็น filesystem-safe
        slug: ตัวระบุสั้นๆ สำหรับไฟล์ที่เป็น filesystem-safe
        input_sha256: ค่าแฮช SHA-256 แบบเต็ม (64 ตัวอักษร) ของข้อความสคริปต์
        base_dir: ไดเรกทอรีฐานสำหรับเก็บไฟล์ (ค่าเริ่มต้น: data/voiceovers)

    Returns:
        tuple ของ (wav_path, metadata_path) ที่สร้างจาก run_id, slug และ input_sha256

    Raises:
        ValueError: ถ้า run_id หรือ slug ไม่ถูกต้อง หรือ input_sha256 ไม่ใช่แฮชความยาว 64 ตัวอักษร
    """
    run_id = _validate_identifier(run_id, "run_id")
    slug = _validate_identifier(slug, "slug")

    if not input_sha256 or len(input_sha256) != 64:
        raise ValueError("input_sha256 must be a full 64-character sha256 hex string")

    base_dir = base_dir or DEFAULT_VOICEOVER_DIR
    base_name = f"{slug}_{input_sha256[:SHA_PREFIX_LENGTH]}"
    wav_path = base_dir / run_id / f"{base_name}.wav"
    metadata_path = base_dir / run_id / f"{base_name}.json"
    return wav_path, metadata_path


def get_wav_duration_seconds(path: Path) -> float:
    """
    คำนวณความยาวของไฟล์ WAV เป็นวินาที

    Args:
        path: พาธของไฟล์ WAV ที่ต้องการอ่าน

    Returns:
        ความยาวของไฟล์เสียงเป็นวินาที (คำนวณจากจำนวน frames หารด้วย sample rate)
        คืนค่า 0.0 ถ้า sample rate <= 0
    """
    with wave.open(str(path), "rb") as wav_file:
        frames = wav_file.getnframes()
        rate = wav_file.getframerate()
    if rate <= 0:
        return 0.0
    return frames / float(rate)


class NullTTSEngine:
    """
    เอนจิน TTS สำหรับการทดสอบที่สร้างไฟล์เสียงเงียบ (silent WAV)

    เอนจินนี้ใช้สำหรับการทดสอบและ development โดยสร้างไฟล์ WAV
    ที่มีเฉพาะเสียงเงียบ (silent audio) ตามความยาวที่กำหนด
    ไม่มีการเรียก external TTS API จริง ทำให้ทดสอบได้เร็วและไม่ต้องใช้ต้นทุน
    """

    name = "null"

    def __init__(
        self,
        duration_seconds: float = NULL_TTS_DURATION_SECONDS,
        sample_rate: int = WAV_SAMPLE_RATE,
    ):
        """
        สร้าง NullTTSEngine instance

        Args:
            duration_seconds: ความยาวของเสียงเงียบที่จะสร้างเป็นวินาที (ต้องมากกว่า 0)
            sample_rate: อัตราการสุ่มตัวอย่างของไฟล์ WAV (ต้องมากกว่า 0)

        Raises:
            ValueError: ถ้า duration_seconds หรือ sample_rate น้อยกว่าหรือเท่ากับ 0
        """
        if duration_seconds <= 0:
            raise ValueError("duration_seconds must be > 0")
        if sample_rate <= 0:
            raise ValueError("sample_rate must be > 0")
        self.duration_seconds = duration_seconds
        self.sample_rate = sample_rate

    def synthesize(self, text: str, output_path: Path) -> None:
        """
        สังเคราะห์เสียงเงียบและบันทึกเป็นไฟล์ WAV

        Args:
            text: ข้อความสคริปต์ (ไม่ถูกใช้ในเอนจินนี้ แต่รักษาไว้ตาม protocol)
            output_path: พาธที่จะบันทึกไฟล์ WAV

        Returns:
            None: เมธอดนี้จะเขียนไฟล์ WAV ไปที่ output_path หรือไม่ทำอะไรถ้า pipeline ถูกปิด
        """
        if not is_pipeline_enabled():
            return

        num_frames = int(round(self.duration_seconds * self.sample_rate))
        silence = b"\x00\x00" * num_frames
        with wave.open(str(output_path), "wb") as wav_file:
            wav_file.setnchannels(WAV_CHANNELS)
            wav_file.setsampwidth(WAV_SAMPLE_WIDTH_BYTES)
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(silence)


def _resolve_root_dir(root_dir: Path | None) -> Path:
    return (root_dir or REPO_ROOT).resolve()


def _resolve_base_dir(root_dir: Path, base_dir: Path | None) -> Path:
    return (base_dir or (root_dir / "data" / "voiceovers")).resolve()


def _relative_to_root(path: Path, root_dir: Path) -> str:
    return path.resolve().relative_to(root_dir).as_posix()


def generate_voiceover(
    script_text: str,
    run_id: str,
    slug: str,
    engine: TTSEngine | None = None,
    *,
    voice: str | None = None,
    style: str | None = None,
    created_utc: str | None = None,
    log: Callable[[str], None] | None = None,
    root_dir: Path | None = None,
    base_dir: Path | None = None,
) -> dict | None:
    """
    สร้างไฟล์เสียง voiceover และ metadata จากข้อความสคริปต์

    ฟังก์ชันหลักของโมดูลที่จัดการการสร้างไฟล์เสียงแบบ deterministic
    โดยใช้ SHA-256 hash ของ script เป็นส่วนหนึ่งของชื่อไฟล์
    รองรับ kill switch (PIPELINE_ENABLED) และสร้าง metadata JSON

    Args:
        script_text: ข้อความสคริปต์ที่ต้องการแปลงเป็นเสียง (ต้องไม่เป็นสตริงว่าง)
        run_id: ตัวระบุการรันที่เป็น filesystem-safe
        slug: ชื่อสั้นๆ สำหรับไฟล์ที่เป็น filesystem-safe
        engine: เอนจิน TTS ที่จะใช้ (ค่าเริ่มต้น: NullTTSEngine)
        voice: พารามิเตอร์เสียงที่ต้องการ (optional, จะบันทึกใน metadata)
        style: สไตล์เสียงที่ต้องการ (optional, จะบันทึกใน metadata)
        created_utc: เวลาที่สร้าง UTC timestamp (optional, จะบันทึกใน metadata)
        log: ฟังก์ชัน callback สำหรับ logging (optional)
        root_dir: ไดเรกทอรีรากของโปรเจกต์ (ค่าเริ่มต้น: REPO_ROOT)
        base_dir: ไดเรกทอรีฐานสำหรับเก็บไฟล์ (ค่าเริ่มต้น: root_dir/data/voiceovers)

    Returns:
        dict ของ metadata ที่มีข้อมูล run_id, slug, input_sha256, output_wav_path,
        duration_seconds, engine_name และฟิลด์ optional อื่นๆ
        คืนค่า None ถ้า pipeline ถูกปิด

    Raises:
        ValueError: ถ้า script_text ว่างเปล่า, base_dir ไม่อยู่ใน root_dir,
            หรือ run_id/slug ไม่ถูกต้อง
        RuntimeError: ถ้าเอนจินไม่สร้างไฟล์ WAV ที่คาดหวัง
    """
    if not is_pipeline_enabled():
        if log:
            log(PIPELINE_DISABLED_MESSAGE)
        return None

    if not isinstance(script_text, str) or not script_text.strip():
        raise ValueError("script_text must be a non-empty string")

    root_dir = _resolve_root_dir(root_dir)
    base_dir = _resolve_base_dir(root_dir, base_dir)
    try:
        base_dir.relative_to(root_dir)
    except ValueError as exc:
        raise ValueError("base_dir must be within root_dir") from exc

    input_sha256 = compute_input_sha256(script_text)
    wav_path, metadata_path = build_voiceover_paths(
        run_id, slug, input_sha256, base_dir=base_dir
    )
    wav_path.parent.mkdir(parents=True, exist_ok=True)

    engine = engine or NullTTSEngine()
    engine.synthesize(script_text, wav_path)

    if not wav_path.exists():
        raise RuntimeError(f"Expected WAV output was not created: {wav_path}")

    duration_seconds = round(get_wav_duration_seconds(wav_path), 6)
    engine_name = getattr(engine, "name", type(engine).__name__)

    metadata: dict[str, object] = {
        "run_id": run_id,
        "slug": slug,
        "input_sha256": input_sha256,
        "output_wav_path": _relative_to_root(wav_path, root_dir),
        "duration_seconds": duration_seconds,
        "engine_name": engine_name,
    }

    if voice is not None:
        metadata["voice"] = voice
    if style is not None:
        metadata["style"] = style
    if created_utc is not None:
        metadata["created_utc"] = created_utc

    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return metadata


def _read_script(script_path: Path | None) -> str:
    """
    อ่านข้อความสคริปต์จากไฟล์หรือ stdin

    Args:
        script_path: พาธของไฟล์สคริปต์ หรือ None เพื่ออ่านจาก stdin

    Returns:
        ข้อความสคริปต์ที่อ่านได้

    Raises:
        ValueError: ถ้า script_path เป็น None และ stdin เป็น terminal (ไม่มีข้อมูล pipe)
    """
    if script_path is None:
        if sys.stdin.isatty():
            raise ValueError("script must be provided via --script or stdin")
        return sys.stdin.read()
    return script_path.read_text(encoding="utf-8")


def cli_main(argv: list[str] | None = None) -> int:
    """
    CLI entry point สำหรับสร้างไฟล์เสียง voiceover

    รับพารามิเตอร์จาก command line และเรียกใช้ generate_voiceover()
    รองรับการอ่านสคริปต์จากไฟล์หรือ stdin

    Args:
        argv: รายการ arguments (ค่าเริ่มต้น: sys.argv[1:])

    Returns:
        0 ถ้าสำเร็จ, 1 ถ้าเกิด error
    """
    parser = argparse.ArgumentParser(
        description="Generate deterministic voiceover WAV + metadata."
    )
    parser.add_argument("--run-id", required=True, help="Run identifier (required)")
    parser.add_argument("--slug", required=True, help="Filesystem-safe slug (required)")
    parser.add_argument(
        "--script",
        type=Path,
        default=None,
        help="Path to script text file (reads stdin if omitted)",
    )
    parser.add_argument("--voice", default=None, help="Optional voice parameter")
    parser.add_argument("--style", default=None, help="Optional style parameter")

    args = parser.parse_args(argv)

    try:
        if not is_pipeline_enabled():
            print(PIPELINE_DISABLED_MESSAGE)
            return 0
        script_text = _read_script(args.script)
        metadata = generate_voiceover(
            script_text,
            args.run_id,
            args.slug,
            voice=args.voice,
            style=args.style,
            log=print,
        )
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if metadata is None:
        return 0

    print("Voiceover generated:")
    print(f"  WAV: {metadata['output_wav_path']}")
    _, metadata_path = build_voiceover_paths(
        args.run_id, args.slug, metadata["input_sha256"], base_dir=DEFAULT_VOICEOVER_DIR
    )
    print(f"  Metadata: {_relative_to_root(metadata_path, REPO_ROOT)}")
    print(f"  Engine: {metadata['engine_name']}")
    print(f"  Duration: {metadata['duration_seconds']}")
    return 0
