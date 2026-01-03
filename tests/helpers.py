from __future__ import annotations

import json
from pathlib import Path


def write_post_templates(base_dir: Path) -> None:
    """
    เขียนไฟล์ template สำหรับ post content (short.md และ long.md) เพื่อใช้ในการทดสอบ

    Args:
        base_dir: โฟลเดอร์หลักสำหรับสร้าง templates/post

    Returns:
        None
    """
    templates_dir = base_dir / "templates" / "post"
    templates_dir.mkdir(parents=True, exist_ok=True)
    (templates_dir / "short.md").write_text(
        "{{hook}}\n{{summary}}\n\n{{cta}}\n{{hashtags}}\n", encoding="utf-8"
    )
    (templates_dir / "long.md").write_text(
        "{{title}}\n\n{{hook}}\n\n{{summary}}\n\n{{cta}}\n\n{{hashtags}}\n",
        encoding="utf-8",
    )


def write_metadata(
    base_dir: Path,
    run_id: str,
    *,
    title: str = "Sample title",
    description: str = "Sample description",
    tags: list[str] | None = None,
    language: str = "en",
    platform: str = "youtube",
) -> Path:
    """
    เขียนไฟล์ metadata.json สำหรับใช้ในการทดสอบ

    Args:
        base_dir: โฟลเดอร์หลัก (มักจะเป็น tmp_path ในเทส)
        run_id: รหัสการรัน เพื่อใช้เป็นชื่อโฟลเดอร์ย่อย
        title: ชื่อวิดีโอ
        description: คำอธิบายวิดีโอ
        tags: รายการแท็ก (ค่าเริ่มต้น: ["#test"])
        language: รหัสภาษาของเนื้อหา (ค่าเริ่มต้น: "en")
        platform: ชื่อแพลตฟอร์ม (ค่าเริ่มต้น: "youtube")

    Returns:
        Path: path ไปยังไฟล์ metadata.json ที่ถูกสร้างขึ้น
    """
    if tags is None:
        tags = ["#test"]

    metadata_path = base_dir / "output" / run_id / "metadata.json"
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata = {
        "title": title,
        "description": description,
        "tags": tags,
        "language": language,
        "platform": platform,
    }
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return metadata_path
