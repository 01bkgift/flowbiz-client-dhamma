"""
ทดสอบโมดูล voiceover_tts สำหรับการสร้างไฟล์เสียงแบบ deterministic

ไฟล์นี้ทดสอบฟีเจอร์ต่างๆ ของระบบ TTS voiceover ได้แก่:
- การสร้างชื่อไฟล์แบบ deterministic จาก content hash
- kill switch (PIPELINE_ENABLED) ที่ไม่ทำให้เกิด side effects
- การสร้างไฟล์ WAV ที่ถูกต้องตามมาตรฐาน
- schema ของ metadata ที่มีความเสถียร
- การป้องกัน path traversal
"""

from __future__ import annotations

import wave
from pathlib import Path

import pytest

from automation_core.voiceover_tts import (
    NULL_TTS_DURATION_SECONDS,
    PIPELINE_DISABLED_MESSAGE,
    WAV_CHANNELS,
    WAV_SAMPLE_RATE,
    WAV_SAMPLE_WIDTH_BYTES,
    NullTTSEngine,
    build_voiceover_paths,
    cli_main,
    compute_input_sha256,
    generate_voiceover,
)


def test_deterministic_output_path():
    """ทดสอบว่าชื่อไฟล์ที่สร้างจาก input เดียวกันจะเหมือนกันเสมอ (deterministic)"""
    run_id = "run_123"
    slug = "demo_slug"
    script = "Hello world"

    input_sha = compute_input_sha256(script)
    wav_path_1, json_path_1 = build_voiceover_paths(run_id, slug, input_sha)
    wav_path_2, json_path_2 = build_voiceover_paths(run_id, slug, input_sha)

    assert wav_path_1 == wav_path_2
    assert json_path_1 == json_path_2
    assert wav_path_1.name == f"{slug}_{input_sha[:12]}.wav"


def test_different_script_changes_output_name():
    """ทดสอบว่าสคริปต์ที่ต่างกันจะสร้างชื่อไฟล์ที่ต่างกัน"""
    run_id = "run_123"
    slug = "demo_slug"

    sha_a = compute_input_sha256("Script A")
    sha_b = compute_input_sha256("Script B")

    wav_a, _ = build_voiceover_paths(run_id, slug, sha_a)
    wav_b, _ = build_voiceover_paths(run_id, slug, sha_b)

    assert sha_a != sha_b
    assert wav_a.name != wav_b.name


def test_kill_switch_no_side_effects(tmp_path, monkeypatch, capsys):
    """ทดสอบว่า kill switch (PIPELINE_ENABLED=false) ไม่สร้างไฟล์หรือไดเรกทอรีใดๆ"""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PIPELINE_ENABLED", "false")

    script_path = tmp_path / "script.txt"
    script_path.write_text("Hello world", encoding="utf-8")
    before = sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*"))

    exit_code = cli_main(
        [
            "--run-id",
            "run_001",
            "--slug",
            "demo",
            "--script",
            str(script_path),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert PIPELINE_DISABLED_MESSAGE in captured.out
    assert not (tmp_path / "data" / "voiceovers").exists()
    after = sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*"))
    assert before == after


def test_null_tts_writes_valid_wav(tmp_path, monkeypatch):
    """ทดสอบว่า NullTTSEngine สร้างไฟล์ WAV ที่ถูกต้องตามพารามิเตอร์ที่กำหนด"""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PIPELINE_ENABLED", "true")

    metadata = generate_voiceover(
        "Short script for testing",
        "run_002",
        "sample",
        engine=NullTTSEngine(),
        root_dir=tmp_path,
    )

    assert metadata is not None
    wav_path = Path(metadata["output_wav_path"])
    assert wav_path.exists()

    with wave.open(str(wav_path), "rb") as wav_file:
        assert wav_file.getnchannels() == WAV_CHANNELS
        assert wav_file.getframerate() == WAV_SAMPLE_RATE
        assert wav_file.getsampwidth() == WAV_SAMPLE_WIDTH_BYTES
        assert wav_file.getnframes() == int(
            round(NULL_TTS_DURATION_SECONDS * WAV_SAMPLE_RATE)
        )

    assert isinstance(metadata["duration_seconds"], (int, float))
    assert metadata["duration_seconds"] > 0


def test_metadata_schema_stable(tmp_path, monkeypatch):
    """ทดสอบว่า metadata JSON มี schema ที่คงที่และตรงตามที่กำหนด"""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PIPELINE_ENABLED", "true")

    metadata = generate_voiceover(
        "Schema check", "run_003", "schema", root_dir=tmp_path
    )
    assert metadata is not None

    required = {
        "run_id",
        "slug",
        "input_sha256",
        "output_wav_path",
        "duration_seconds",
        "engine_name",
    }
    optional = {"voice", "style", "created_utc"}
    assert required.issubset(metadata.keys())
    assert set(metadata.keys()).issubset(required | optional)
    assert isinstance(metadata["run_id"], str)
    assert isinstance(metadata["slug"], str)
    assert isinstance(metadata["input_sha256"], str)
    assert len(metadata["input_sha256"]) == 64
    assert isinstance(metadata["output_wav_path"], str)
    assert metadata["output_wav_path"].startswith("data/voiceovers/")
    assert not Path(metadata["output_wav_path"]).is_absolute()
    assert not (
        len(metadata["output_wav_path"]) >= 3
        and metadata["output_wav_path"][1:3] in {":\\", ":/"}
    )
    assert isinstance(metadata["duration_seconds"], (int, float))
    assert isinstance(metadata["engine_name"], str)
    if "voice" in metadata:
        assert isinstance(metadata["voice"], str)
    if "style" in metadata:
        assert isinstance(metadata["style"], str)
    if "created_utc" in metadata:
        assert isinstance(metadata["created_utc"], str)


def test_slug_rejects_path_traversal(tmp_path, monkeypatch):
    """ทดสอบว่าระบบป้องกัน path traversal ใน slug ได้อย่างถูกต้อง"""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PIPELINE_ENABLED", "true")

    with pytest.raises(ValueError):
        generate_voiceover("test", "run_004", "bad/slug", root_dir=tmp_path)

    with pytest.raises(ValueError):
        generate_voiceover("test", "run_004", "bad\\slug", root_dir=tmp_path)

    with pytest.raises(ValueError):
        generate_voiceover("test", "run_004", "..", root_dir=tmp_path)
