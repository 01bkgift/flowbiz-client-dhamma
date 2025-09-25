#!/usr/bin/env python3

"""
Manual test สำหรับ ScriptWriterAgent
ทดสอบการทำงานจริงของ Agent และแสดงผลลัพธ์
"""

import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agents.research_retrieval.model import Passage
from agents.script_outline import (
    RetentionGoals,
    ScriptOutlineAgent,
    ScriptOutlineInput,
    StylePreferences,
    ViewerPersona,
)
from agents.script_writer import (
    PassageData,
    ScriptWriterAgent,
    ScriptWriterInput,
    StyleNotes,
)


def create_test_outline():
    """สร้าง sample outline สำหรับทดสอบ"""
    outline_agent = ScriptOutlineAgent()

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
            pain_points=["เครียดจากการทำงาน", "นอนไม่หลับ", "วิตกกังวล"],
            desired_state="ใจสงบ นอนหลับสนิท มีความสุข",
        ),
        style_preferences=StylePreferences(
            tone="อบอุ่น สงบ ไม่สั่งสอน", avoid=["ศัพท์บาลีหนักเกินไป", "การตำหนิตัวผู้ชม"]
        ),
        retention_goals=RetentionGoals(
            hook_drop_max_pct=30, mid_segment_break_every_sec=120
        ),
    )

    return outline_agent.run(input_data)


def create_test_passages():
    """สร้าง sample passages สำหรับทดสอบ"""
    primary_passages = [
        Passage(
            id="p123",
            source_name="มหาสติปฏฐานสูตร",
            collection="พระสุตตันตปิฎก",
            canonical_ref="DN 22",
            original_text="สติปฏฐานเป็นเครื่องฝึกจิตให้มีความสงบและปัญญา การสังเกตกายเวทนาจิตธรรมอรรถ",
            thai_modernized="การตั้งสติเป็นวิธีฝึกจิตให้สงบและเกิดปัญญา โดยสังเกตร่างกาย ความรู้สึก จิตใจ และสิ่งต่างๆ",
            relevance_final=0.95,
            doctrinal_tags=["สติ", "สติปฏฐาน", "สมาธิ"],
            license="public_domain",
            reason="หลักการฝึกสติที่เกี่ยวข้องตรงกับเรื่องความกังวล",
        ),
        Passage(
            id="p210",
            source_name="อานาปานสติสูตร",
            collection="พระสุตตันตปิฎก",
            canonical_ref="MN 118",
            original_text="อานาปานสติเมื่อพัฒนาแล้วย่อมนำไปสู่ความสงบ ผู้ฝึกพึงตั้งสติดูลมหายใจเข้าออก",
            thai_modernized="การสติดูลมหายใจที่พัฒนาแล้วจะทำให้ใจสงบ ผู้ฝึกควรตั้งสติสังเกตลมหายใจเข้าออก",
            relevance_final=0.9,
            doctrinal_tags=["อานาปานสติ", "สมาธิ", "ความสงบ"],
            license="public_domain",
            reason="วิธีการหายใจเพื่อความสงบก่อนนอน",
        ),
        Passage(
            id="p345",
            source_name="สัญญุตตนิกาย",
            collection="พระสุตตันตปิฎก",
            canonical_ref="SN 36.6",
            original_text="เวทนาสามประการ สุขเวทนา ทุกข์เวทนา อทุกขมสุขเวทนา ถ้ารู้แจ้งแล้วย่อมไม่ยึดติด",
            thai_modernized="ความรู้สึก 3 แบบ คือ รู้สึกสุข ทุกข์ และเป็นกลาง ถ้ารู้จักแล้วจะไม่ยึดติด",
            relevance_final=0.85,
            doctrinal_tags=["เวทนา", "ไตรลักษณ์", "ปล่อยวาง"],
            license="public_domain",
            reason="การรู้จักเวทนาช่วยปล่อยวางความกังวล",
        ),
    ]

    supportive_passages = [
        Passage(
            id="p456",
            source_name="วิสุทธิมรรค",
            collection="พระอภิธรรมปิฎก",
            canonical_ref="Vism IV",
            original_text="เมตตาคือความรักเอ็นดู ปรารถนาดีต่อสัตว์ทั้งหลาย เริ่มจากตัวเอง แล้วขยายไปสู่ผู้อื่น",
            thai_modernized="เมตตาคือความรักใคร่ปรารถนาดีต่อทุกชีวิต เริ่มรักตัวเองก่อน แล้วค่อยขยายไปสู่คนอื่น",
            relevance_final=0.7,
            doctrinal_tags=["เมตตา", "พรหมวิหาร", "ความรัก"],
            license="public_domain",
            reason="เมตตาช่วยคลายความตึงเครียดก่อนนอน",
        )
    ]

    return PassageData(primary=primary_passages, supportive=supportive_passages)


def test_script_writer_agent():
    """ทดสอบ ScriptWriterAgent แบบ manual"""

    print("🚀 เริ่มทดสอบ ScriptWriterAgent...")

    # สร้าง agent
    agent = ScriptWriterAgent()
    print(f"✅ สร้าง {agent.name} v{agent.version} สำเร็จ")

    # สร้าง outline และ passages
    print("📋 กำลังสร้าง outline...")
    outline = create_test_outline()

    print("📚 กำลังสร้าง passages...")
    passages = create_test_passages()

    # สร้าง input data
    input_data = ScriptWriterInput(
        outline=outline,
        passages=passages,
        style_notes=StyleNotes(
            tone="อบอุ่น สงบ ไม่สั่งสอน",
            voice="เป็นกันเอง สุภาพ ใช้คำว่า เรา/คุณ",
            avoid=["ศัพท์บาลีติดกันหลายคำ", "การชี้นำผลลัพธ์แน่นอน"],
        ),
        target_seconds=600,
        language="th",
    )

    print(f"📝 สร้าง input สำหรับหัวข้อ: {input_data.outline.topic}")
    print(f"   - Outline sections: {len(input_data.outline.outline)}")
    print(f"   - Primary passages: {len(input_data.passages.primary)}")
    print(f"   - Supportive passages: {len(input_data.passages.supportive)}")
    print(f"   - Target duration: {input_data.target_seconds} วินาที")

    # ประมวลผลด้วย agent
    try:
        print("\n⚙️ กำลังเรียบเรียงสคริปต์...")
        result = agent.run(input_data)
        print("✅ Agent ประมวลผลสำเร็จ!")

        # แสดงผลลัพธ์
        print("\n📊 ผลลัพธ์:")
        print(f"   - หัวข้อ: {result.topic}")
        print(f"   - จำนวน segments: {len(result.segments)}")
        print(f"   - ระยะเวลารวม: {result.duration_est_total} วินาที")
        print(f"   - Citations ที่ใช้: {len(result.citations_used)} รายการ")
        print(f"   - Unmatched citations: {len(result.unmatched_citations)} รายการ")

        print("\n📈 Meta information:")
        print(f"   - Reading speed: {result.meta.reading_speed_wpm} WPM")
        print(f"   - Retention cues: {result.meta.interrupts_count} ตัว")
        print(f"   - Teaching segments: {result.meta.teaching_segments} ชิ้น")
        print(f"   - Practice steps: {result.meta.practice_steps_count} ขั้นตอน")

        print("\n✅ Quality Check:")
        qc = result.quality_check
        print(f"   - Citations valid: {qc.citations_valid}")
        print(f"   - Teaching has citation: {qc.teaching_has_citation}")
        print(f"   - Duration within range: {qc.duration_within_range}")
        print(f"   - Hook within 8s: {qc.hook_within_8s}")
        print(f"   - No prohibited claims: {qc.no_prohibited_claims}")

        if result.warnings:
            print("\n⚠️ Warnings:")
            for warning in result.warnings:
                print(f"   - {warning}")

        print("\n📝 Script Segments:")
        for i, segment in enumerate(result.segments):
            print(
                f"\n{i + 1}. {segment.segment_type.value.upper()} ({segment.est_seconds}s)"
            )
            print(f"   {segment.text}")

        print(f"\n🎯 Citations used: {', '.join(result.citations_used)}")

        # บันทึกผลลัพธ์เป็น JSON
        output_path = Path("/tmp/script_writer_test_result.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result.model_dump(), f, ensure_ascii=False, indent=2)
        print(f"\n💾 บันทึกผลลัพธ์ไว้ที่: {output_path}")

        return True

    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาด: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_script_writer_agent()
    sys.exit(0 if success else 1)
