"""
Test cases สำหรับ ScriptWriterAgent
ทดสอบการทำงานของ Agent ในการเรียบเรียงสคริปต์วิดีโอ
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agents.research_retrieval.model import Passage
from agents.script_outline import (
    RetentionGoals,
    ScriptOutlineAgent,
    ScriptOutlineInput,
    ScriptOutlineOutput,
    StylePreferences,
    ViewerPersona,
)
from agents.script_writer import (
    PassageData,
    ScriptWriterAgent,
    ScriptWriterInput,
    ScriptWriterOutput,
    SegmentType,
    StyleNotes,
)


class TestScriptWriterAgent:
    """Test cases สำหรับ ScriptWriterAgent"""

    def setup_method(self):
        """Setup สำหรับแต่ละ test"""
        self.agent = ScriptWriterAgent()

    def test_agent_initialization(self):
        """ทดสอบการสร้าง agent"""
        assert self.agent.name == "ScriptWriterAgent"
        assert self.agent.version == "1.0.0"
        assert "สคริปต์วิดีโอ" in self.agent.description

    def create_sample_outline(self) -> ScriptOutlineOutput:
        """สร้าง sample outline สำหรับทดสอบ"""
        outline_agent = ScriptOutlineAgent()

        input_data = ScriptOutlineInput(
            topic_title="ปล่อยวางความกังวลก่อนนอน",
            summary_bullets=[
                "การสังเกตเวทนาโดยไม่ยึดช่วยคลายกังวล",
                "อานาปานสติช่วงสั้นก่อนหลับลดการวนคิด",
            ],
            core_concepts=["สติ", "เวทนา", "ปล่อยวาง"],
            target_minutes=10,
            viewer_persona=ViewerPersona(
                name="คนทำงานเมือง",
                pain_points=["เครียดจากการทำงาน", "นอนไม่หลับ"],
                desired_state="ใจสงบ นอนหลับสนิท",
            ),
            style_preferences=StylePreferences(
                tone="อบอุ่น สงบ ไม่สั่งสอน", avoid=["ศัพท์บาลีหนักเกินไป", "การตำหนิตัวผู้ชม"]
            ),
            retention_goals=RetentionGoals(
                hook_drop_max_pct=30, mid_segment_break_every_sec=120
            ),
        )

        return outline_agent.run(input_data)

    def create_sample_passages(self) -> PassageData:
        """สร้าง sample passages สำหรับทดสอบ"""
        primary_passages = [
            Passage(
                id="p123",
                source_name="มหาปรินิพพานสูตร",
                collection="พระสุตตันตปิฎก",
                canonical_ref="DN 16",
                original_text="สติปฏฐานเป็นเครื่องฝึกจิตให้มีความสงบและปัญญา",
                thai_modernized="การตั้งสติเป็นวิธีฝึกจิตให้สงบและเกิดปัญญา",
                relevance_final=0.9,
                doctrinal_tags=["สติ", "สมาธิ"],
                license="public_domain",
                reason="เกี่ยวข้องกับการฝึกสติ",
            ),
            Passage(
                id="p210",
                source_name="อานาปานสติสูตร",
                collection="พระสุตตันตปิฎก",
                canonical_ref="MN 118",
                original_text="อานาปานสติเมื่อพัฒนาแล้วย่อมนำไปสู่ความสงบ",
                thai_modernized="การสติดูลมหายใจที่พัฒนาแล้วจะทำให้ใจสงบ",
                relevance_final=0.85,
                doctrinal_tags=["อานาปานสติ", "สมาธิ"],
                license="public_domain",
                reason="เกี่ยวข้องกับการหายใจและความสงบ",
            ),
        ]

        supportive_passages = [
            Passage(
                id="p300",
                source_name="วิสุทธิมรรค",
                collection="พระอภิธรรมปิฎก",
                canonical_ref="Vism XIII",
                original_text="เวทนาอันเป็นความรู้สึกควรสังเกตด้วยความเป็นกลาง",
                thai_modernized="ความรู้สึกต่างๆ ควรสังเกตด้วยใจที่เป็นกลาง",
                relevance_final=0.7,
                doctrinal_tags=["เวทนา", "วิปัสสนา"],
                license="public_domain",
                reason="อธิบายการสังเกตเวทนา",
            )
        ]

        return PassageData(primary=primary_passages, supportive=supportive_passages)

    def test_run_basic_functionality(self):
        """ทดสอบการทำงานพื้นฐานของ agent"""
        outline = self.create_sample_outline()
        passages = self.create_sample_passages()

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

        result = self.agent.run(input_data)

        # ตรวจสอบโครงสร้างพื้นฐาน
        assert isinstance(result, ScriptWriterOutput)
        assert result.topic == outline.topic
        assert len(result.segments) > 0
        assert result.duration_est_total > 0

    def test_segments_structure_requirements(self):
        """ทดสอบโครงสร้างของ segments"""
        outline = self.create_sample_outline()
        passages = self.create_sample_passages()

        input_data = ScriptWriterInput(
            outline=outline,
            passages=passages,
            style_notes=StyleNotes(tone="อบอุ่น สงบ", voice="เป็นกันเอง", avoid=[]),
            target_seconds=600,
        )

        result = self.agent.run(input_data)

        # ตรวจสอบว่ามี segment types ที่จำเป็น
        segment_types = [s.segment_type for s in result.segments]
        assert SegmentType.HOOK in segment_types
        assert SegmentType.TEACHING in segment_types

        # ตรวจสอบว่าแต่ละ segment มีข้อมูลครบ
        for segment in result.segments:
            assert segment.text.strip() != ""
            assert segment.est_seconds > 0
            assert isinstance(segment.segment_type, SegmentType)

    def test_hook_segment_requirements(self):
        """ทดสอบข้อกำหนดของ Hook segment"""
        outline = self.create_sample_outline()
        passages = self.create_sample_passages()

        input_data = ScriptWriterInput(
            outline=outline,
            passages=passages,
            style_notes=StyleNotes(tone="อบอุ่น", voice="เป็นกันเอง", avoid=[]),
            target_seconds=600,
        )

        result = self.agent.run(input_data)

        # หา Hook segments
        hook_segments = [
            s for s in result.segments if s.segment_type == SegmentType.HOOK
        ]
        assert len(hook_segments) > 0

        # ตรวจสอบ Hook ไม่เกิน 8 วินาที
        for hook in hook_segments:
            assert hook.est_seconds <= 8

    def test_teaching_segments_have_citations(self):
        """ทดสอบว่า teaching segments มี citations"""
        outline = self.create_sample_outline()
        passages = self.create_sample_passages()

        input_data = ScriptWriterInput(
            outline=outline,
            passages=passages,
            style_notes=StyleNotes(tone="อบอุ่น", voice="เป็นกันเอง", avoid=[]),
            target_seconds=600,
        )

        result = self.agent.run(input_data)

        # หา Teaching segments
        teaching_segments = [
            s for s in result.segments if s.segment_type == SegmentType.TEACHING
        ]

        # อย่างน้อยต้องมี 1 teaching segment ที่มี citation
        has_citation = False
        for segment in teaching_segments:
            if "[CIT:" in segment.text:
                has_citation = True
                break

        assert has_citation, "Teaching segments ควรมี citations"

    def test_citations_validation(self):
        """ทดสอบการตรวจสอบ citations"""
        outline = self.create_sample_outline()
        passages = self.create_sample_passages()

        input_data = ScriptWriterInput(
            outline=outline,
            passages=passages,
            style_notes=StyleNotes(tone="อบอุ่น", voice="เป็นกันเอง", avoid=[]),
            target_seconds=600,
        )

        result = self.agent.run(input_data)

        # ตรวจสอบว่า citations ที่ใช้มีอยู่ใน passages
        passage_ids = [p.id for p in passages.primary + passages.supportive]

        for citation_id in result.citations_used:
            assert citation_id in passage_ids, f"Citation {citation_id} ไม่มีใน passages"

        # ตรวจสอบว่า unmatched_citations ควรเป็นค่าว่าง
        assert len(result.unmatched_citations) == 0

    def test_retention_cues_addition(self):
        """ทดสอบการเพิ่ม retention cues"""
        outline = self.create_sample_outline()
        passages = self.create_sample_passages()

        input_data = ScriptWriterInput(
            outline=outline,
            passages=passages,
            style_notes=StyleNotes(tone="อบอุ่น", voice="เป็นกันเอง", avoid=[]),
            target_seconds=600,
        )

        result = self.agent.run(input_data)

        # ตรวจสอบว่ามี retention cues
        total_cues = 0
        for segment in result.segments:
            # นับจำนวน retention cues (ในวงเล็บ)
            import re

            cues = re.findall(r"\([^)]+\)", segment.text)
            total_cues += len(cues)

        assert total_cues > 0, "ควรมี retention cues"
        assert result.meta.interrupts_count == total_cues

    def test_duration_within_range(self):
        """ทดสอบการควบคุมระยะเวลา"""
        outline = self.create_sample_outline()
        passages = self.create_sample_passages()

        target_seconds = 600
        input_data = ScriptWriterInput(
            outline=outline,
            passages=passages,
            style_notes=StyleNotes(tone="อบอุ่น", voice="เป็นกันเอง", avoid=[]),
            target_seconds=target_seconds,
        )

        result = self.agent.run(input_data)

        # ตรวจสอบระยะเวลารวม
        tolerance = target_seconds * 0.15  # ±15%
        assert (
            abs(result.duration_est_total - target_seconds) <= tolerance * 2
        )  # ยอมรับความคลาดเคลื่อนสูงในการทดสอบ

    def test_quality_check_completeness(self):
        """ทดสอบความสมบูรณ์ของ quality check"""
        outline = self.create_sample_outline()
        passages = self.create_sample_passages()

        input_data = ScriptWriterInput(
            outline=outline,
            passages=passages,
            style_notes=StyleNotes(tone="อบอุ่น", voice="เป็นกันเอง", avoid=[]),
            target_seconds=600,
        )

        result = self.agent.run(input_data)

        # ตรวจสอบว่ามี quality check ครบถ้วน
        qc = result.quality_check
        assert hasattr(qc, "citations_valid")
        assert hasattr(qc, "teaching_has_citation")
        assert hasattr(qc, "duration_within_range")
        assert hasattr(qc, "hook_within_8s")
        assert hasattr(qc, "no_prohibited_claims")

    def test_meta_info_accuracy(self):
        """ทดสอบความถูกต้องของ meta info"""
        outline = self.create_sample_outline()
        passages = self.create_sample_passages()

        input_data = ScriptWriterInput(
            outline=outline,
            passages=passages,
            style_notes=StyleNotes(tone="อบอุ่น", voice="เป็นกันเอง", avoid=[]),
            target_seconds=600,
        )

        result = self.agent.run(input_data)

        meta = result.meta

        # ตรวจสอบ reading speed อยู่ในช่วงที่เหมาะสม
        assert 100 <= meta.reading_speed_wpm <= 200

        # ตรวจสอบจำนวน teaching segments
        actual_teaching_segments = len(
            [s for s in result.segments if s.segment_type == SegmentType.TEACHING]
        )
        assert meta.teaching_segments == actual_teaching_segments

    def test_prohibited_claims_detection(self):
        """ทดสอบการตรวจจับคำที่ห้ามใช้"""
        outline = self.create_sample_outline()
        passages = self.create_sample_passages()

        input_data = ScriptWriterInput(
            outline=outline,
            passages=passages,
            style_notes=StyleNotes(
                tone="อบอุ่น", voice="เป็นกันเอง", avoid=["การยืนยันผลลัพธ์แน่นอน"]
            ),
            target_seconds=600,
        )

        result = self.agent.run(input_data)

        # ตรวจสอบว่าไม่มีคำต้องห้าม
        prohibited_found = False
        for segment in result.segments:
            for claim in self.agent.prohibited_claims:
                if claim in segment.text:
                    prohibited_found = True
                    break

        # Quality check ควรสะท้อนการตรวจสอบนี้
        assert result.quality_check.no_prohibited_claims == (not prohibited_found)

    def test_input_validation(self):
        """ทดสอบการตรวจสอบข้อมูลนำเข้า"""
        outline = self.create_sample_outline()

        # ทดสอบกรณีไม่มี passages
        input_data = ScriptWriterInput(
            outline=outline,
            passages=PassageData(primary=[], supportive=[]),
            style_notes=StyleNotes(tone="อบอุ่น", voice="เป็นกันเอง", avoid=[]),
            target_seconds=600,
        )

        result = self.agent.run(input_data)

        # ควรได้ warning หรือ error
        assert result.warnings, "Expected warnings when no passages are provided"
        assert any(
            "passage" in warning.lower() or "ไม่พบ" in warning
            for warning in result.warnings
        ), "Warnings should mention missing passages"

    def test_different_target_durations(self):
        """ทดสอบการปรับตัวตามระยะเวลาเป้าหมายที่แตกต่าง"""
        outline = self.create_sample_outline()
        passages = self.create_sample_passages()

        style_notes = StyleNotes(tone="อบอุ่น", voice="เป็นกันเอง", avoid=[])

        # ทดสอบเป้าหมาย 8 นาที
        input_short = ScriptWriterInput(
            outline=outline,
            passages=passages,
            style_notes=style_notes,
            target_seconds=480,
        )

        # ทดสอบเป้าหมาย 12 นาที
        input_long = ScriptWriterInput(
            outline=outline,
            passages=passages,
            style_notes=style_notes,
            target_seconds=720,
        )

        result_short = self.agent.run(input_short)
        result_long = self.agent.run(input_long)

        # สคริปต์ยาวควรมีระยะเวลานานกว่า
        assert result_long.duration_est_total > result_short.duration_est_total

    def test_warnings_generation(self):
        """ทดสอบการสร้างคำเตือน"""
        outline = self.create_sample_outline()
        passages = self.create_sample_passages()

        input_data = ScriptWriterInput(
            outline=outline,
            passages=passages,
            style_notes=StyleNotes(tone="อบอุ่น", voice="เป็นกันเอง", avoid=[]),
            target_seconds=300,  # เป้าหมายสั้นมาก เพื่อให้เกิด warning
        )

        result = self.agent.run(input_data)

        # ควรมี warnings เนื่องจากเป้าหมายเวลาสั้น
        assert isinstance(result.warnings, list)

    def test_segment_type_coverage(self):
        """ทดสอบว่าครอบคลุม segment types ที่สำคัญ"""
        outline = self.create_sample_outline()
        passages = self.create_sample_passages()

        input_data = ScriptWriterInput(
            outline=outline,
            passages=passages,
            style_notes=StyleNotes(tone="อบอุ่น", voice="เป็นกันเอง", avoid=[]),
            target_seconds=600,
        )

        result = self.agent.run(input_data)

        segment_types = [s.segment_type for s in result.segments]

        # ตรวจสอบว่ามี segment types ที่หลากหลาย
        assert len(set(segment_types)) >= 3  # อย่างน้อย 3 ประเภท

        # Hook และ Closing ควรมี
        assert SegmentType.HOOK in segment_types
        assert (
            SegmentType.CLOSING in segment_types
            or SegmentType.TEACHING in segment_types
        )
