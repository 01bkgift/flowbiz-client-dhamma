#!/usr/bin/env python3
"""
Manual test สำหรับ ScriptOutlineAgent
ทดสอบการทำงานจริงของ Agent และแสดงผลลัพธ์
"""

import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agents.script_outline import (
    RetentionGoals,
    ScriptOutlineAgent,
    ScriptOutlineInput,
    StylePreferences,
    ViewerPersona,
)


def test_script_outline_agent():
    """ทดสอบ ScriptOutlineAgent แบบ manual"""

    print("🚀 เริ่มทดสอบ ScriptOutlineAgent...")

    # สร้าง agent
    agent = ScriptOutlineAgent()
    print(f"✅ สร้าง {agent.name} v{agent.version} สำเร็จ")

    # สร้าง input data
    input_data = ScriptOutlineInput(
        topic_title="ปล่อยวางความกังวลก่อนนอน",
        summary_bullets=[
            "การสังเกตเวทนาโดยไม่ยึดช่วยคลายกังวล",
            "อานาปานสติช่วงสั้นก่อนหลับลดการวนคิด",
            "การยอมรับความไม่แน่นอนทำให้ใจคลาย",
        ],
        core_concepts=["สติ", "เวทนา", "ปล่อยวาง", "อานาปานสติ"],
        missing_concepts=["เมตตา"],
        target_minutes=10,
        viewer_persona=ViewerPersona(
            name="คนทำงานเมือง",
            pain_points=["นอนไม่ค่อยหลับ", "คิดเรื่องงานซ้ำ", "กังวลอนาคต"],
            desired_state="ใจผ่อนคลาย หลับง่ายขึ้น",
        ),
        style_preferences=StylePreferences(
            tone="อบอุ่น สงบ ไม่สั่งสอน", avoid=["ศัพท์บาลีหนักเกินไปติดๆกัน", "การตำหนิตัวผู้ชม"]
        ),
        retention_goals=RetentionGoals(
            hook_drop_max_pct=30, mid_segment_break_every_sec=120
        ),
    )

    print(f"📋 สร้าง input สำหรับหัวข้อ: {input_data.topic_title}")

    # ประมวลผลด้วย agent
    try:
        result = agent.run(input_data)
        print("✅ Agent ประมวลผลสำเร็จ!")

        # แสดงผลลัพธ์
        print("\n📊 ผลลัพธ์:")
        print(f"   หัวข้อ: {result.topic}")
        print(f"   เป้าหมายความยาว: {result.duration_target_min} นาที")
        print(f"   เวลารวมที่คำนวณได้: {result.pacing_check.total_est_seconds} วินาที")
        print(f"   จำนวนส่วนทั้งหมด: {len(result.outline)} ส่วน")
        print(
            f"   อยู่ในช่วงเป้าหมาย: {'✅' if result.pacing_check.within_range else '❌'}"
        )

        print("\n📋 โครงร่างทั้งหมด:")
        for i, section in enumerate(result.outline, 1):
            print(f"   {i}. {section.section} ({section.est_seconds}s)")
            if section.hook_pattern:
                print(f"      Hook Pattern: {section.hook_pattern}")
            if section.content_draft:
                print(f"      Content: {section.content_draft}")
            if section.retention_tags:
                print(f"      Retention Tags: {', '.join(section.retention_tags)}")

        print("\n🎯 Hook Variants:")
        for i, variant in enumerate(result.hook_variants, 1):
            print(f"   {i}. {variant}")

        print("\n📈 การครอบคลุมแนวคิด:")
        print(f"   คาดหวัง: {result.concept_coverage.expected}")
        print(f"   ครอบคลุมแล้ว: {result.concept_coverage.covered}")
        print(f"   ขาดหายไป: {result.concept_coverage.missing}")
        print(f"   อัตราส่วน: {result.concept_coverage.coverage_ratio:.2%}")

        if result.warnings:
            print("\n⚠️  คำเตือน:")
            for warning in result.warnings:
                print(f"   - {warning}")

        print("\n🔧 Metadata:")
        print(f"   Hook Pattern ที่เลือก: {result.meta.hook_pattern_selected}")
        print(
            f"   Retention Patterns ที่ใช้: {len(result.meta.retention_patterns_used)} แบบ"
        )
        print(
            f"   Interrupt Spacing OK: {'✅' if result.meta.interrupt_spacing_ok else '❌'}"
        )

        # บันทึกผลลัพธ์เป็น JSON
        output_file = (
            Path(__file__).parent.parent / "output" / "script_outline_test_result.json"
        )
        output_file.parent.mkdir(exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result.model_dump(), f, ensure_ascii=False, indent=2, default=str)

        print(f"\n💾 บันทึกผลลัพธ์ไปที่: {output_file}")

        return True

    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาด: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_script_outline_agent()
    sys.exit(0 if success else 1)
