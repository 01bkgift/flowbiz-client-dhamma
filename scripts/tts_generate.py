#!/usr/bin/env python3
"""
สคริปต์ CLI wrapper สำหรับสร้างไฟล์เสียง voiceover

สคริปต์นี้ทำหน้าที่เป็น wrapper เพื่อเรียกใช้โมดูล voiceover_tts ผ่าน command line
รองรับการรับข้อมูลจากไฟล์สคริปต์หรือ stdin และสร้างไฟล์ WAV พร้อม metadata
ตามระบบ content-addressed naming ที่เป็น deterministic

วิธีใช้งาน:
    python scripts/tts_generate.py --run-id RUN_001 --slug demo --script script.txt
    echo "Hello" | python scripts/tts_generate.py --run-id RUN_001 --slug demo
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from automation_core.voiceover_tts import cli_main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(cli_main())
