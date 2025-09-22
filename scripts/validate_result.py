#!/usr/bin/env python3
"""
Validate JSON result from TrendScoutAgent output.

ตรวจสอบ:
- topics ≤ 15
- composite เรียงจากมากไปน้อย
- ทุก score (search_intent, freshness, evergreen, brand_fit, composite) ∈ [0,1]
- title ≤ 34 ตัวอักษร
"""

import json
import sys
from pathlib import Path

# Remove unused imports - validation script is simple enough


def validate_result(file_path: str = "output/preflight_result.json") -> bool:
    """
    Validate TrendScout JSON output

    Args:
        file_path: Path to JSON file

    Returns:
        True if validation passes

    Raises:
        SystemExit: With code 1 for validation errors, 0 for success
    """
    try:
        path = Path(file_path)
        if not path.exists():
            print(f"❌ ไม่พบไฟล์: {file_path}")
            return False

        with open(path, encoding="utf-8") as f:
            data = json.load(f)

    except json.JSONDecodeError as e:
        print(f"❌ ไฟล์ JSON ไม่ถูกต้อง: {e}")
        return False
    except Exception as e:
        print(f"❌ ไม่สามารถอ่านไฟล์ได้: {e}")
        return False

    # ตรวจสอบโครงสร้างพื้นฐาน
    if not isinstance(data, dict):
        print("❌ ข้อมูลต้องเป็น dictionary")
        return False

    if "topics" not in data:
        print("❌ ไม่พบ key 'topics'")
        return False

    topics = data["topics"]
    if not isinstance(topics, list):
        print("❌ 'topics' ต้องเป็น list")
        return False

    # ตรวจสอบจำนวนหัวข้อ
    if len(topics) > 15:
        print(f"❌ พบหัวข้อ {len(topics)} รายการ (สูงสุด 15)")
        return False

    if len(topics) == 0:
        print("❌ ต้องมีหัวข้ออย่างน้อย 1 รายการ")
        return False

    # ตรวจสอบแต่ละหัวข้อ
    score_fields = ["search_intent", "freshness", "evergreen", "brand_fit", "composite"]
    previous_composite = 1.0  # เริ่มจากสูงสุด

    for i, topic in enumerate(topics):
        if not isinstance(topic, dict):
            print(f"❌ หัวข้อ #{i + 1} ต้องเป็น dictionary")
            return False

        # ตรวจสอบ title
        if "title" not in topic:
            print(f"❌ หัวข้อ #{i + 1} ไม่มี 'title'")
            return False

        title = topic["title"]
        if not isinstance(title, str):
            print(f"❌ หัวข้อ #{i + 1} title ต้องเป็น string")
            return False

        if len(title) > 34:
            print(
                f"❌ หัวข้อ #{i + 1} title ยาวเกิน 34 ตัวอักษร: '{title}' ({len(title)} ตัวอักษร)"
            )
            return False

        # ตรวจสอบคะแนน (อาจอยู่ในโครงสร้าง scores nested object)
        scores_obj = topic.get("scores", topic)  # รองรับทั้ง flat และ nested structure

        for field in score_fields:
            if field not in scores_obj:
                print(f"❌ หัวข้อ #{i + 1} ไม่มี '{field}' ใน scores")
                return False

            score = scores_obj[field]
            if not isinstance(score, int | float):
                print(f"❌ หัวข้อ #{i + 1} {field} ต้องเป็นตัวเลข")
                return False

            if not (0.0 <= score <= 1.0):
                print(f"❌ หัวข้อ #{i + 1} {field} ต้องอยู่ในช่วง [0,1]: {score}")
                return False

        # ตรวจสอบ composite score เรียงลำดับ
        composite = scores_obj["composite"]
        if composite > previous_composite + 0.001:  # อนุญาต floating point error เล็กน้อย
            print(
                f"❌ หัวข้อ #{i + 1} composite score ไม่เรียงจากมากไปน้อย: {composite} > {previous_composite}"
            )
            return False
        previous_composite = composite

    print("✅ Validation OK")
    return True


def main():
    """Main entry point"""
    file_path = sys.argv[1] if len(sys.argv) > 1 else "output/preflight_result.json"

    success = validate_result(file_path)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
