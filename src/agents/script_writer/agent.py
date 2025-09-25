"""
ScriptWriterAgent - Agent สำหรับเรียบเรียงสคริปต์วิดีโอ

Agent นี้แปลงโครงร่างและข้อความอ้างอิงเป็นสคริปต์วิดีโอภาษาไทยที่สมบูรณ์
พร้อมการอ้างอิง citations และ retention cues ตามมาตรฐานของช่อง YouTube ธรรมะดีดี
"""

import logging
import re

from automation_core.base_agent import BaseAgent

from .model import (
    QualityCheck,
    ScriptMeta,
    ScriptSegment,
    ScriptWriterInput,
    ScriptWriterOutput,
    SegmentType,
)

logger = logging.getLogger(__name__)


class ScriptWriterAgent(BaseAgent[ScriptWriterInput, ScriptWriterOutput]):
    """Agent สำหรับเรียบเรียงสคริปต์วิดีโอจากโครงร่างและข้อความอ้างอิง"""

    def __init__(self):
        super().__init__(
            name="ScriptWriterAgent",
            version="1.0.0",
            description="เรียบเรียงสคริปต์วิดีโอภาษาไทยจาก Outline และ Passages พร้อม citations และ retention cues",
        )

        # Retention cues ที่ใช้ได้
        self.retention_cues = [
            "(หายใจลึกๆ 1 ครั้ง)",
            "(หยุด 1 วินาที)",
            "(เสียงกระดิ่งนุ่ม)",
            "(ขึ้นคำคมสั้น 1 บรรทัด)",
            "(หยุด 2 วินาที)",
            "(หายใจเบาๆ)",
        ]

        # คำที่ห้ามใช้เพราะเป็นการยืนยันผลแน่นอน
        self.prohibited_claims = [
            "100%",
            "รับรอง",
            "การันตี",
            "แน่นอน",
            "ได้แน่",
            "หลับได้แน่",
            "หายได้แน่",
            "จะได้",
            "ต้องได้",
        ]

        # ค่าเฉลี่ยความเร็วอ่านภาษาไทย (คำต่อนาที)
        self.avg_reading_speed = 145

        # Segment type mapping จาก outline sections
        self.section_to_segment_type = {
            "Hook": SegmentType.HOOK,
            "Problem Amplify": SegmentType.PROBLEM,
            "Transition Prompt": SegmentType.TRANSITION,
            "Story / Analogy": SegmentType.STORY,
            "Core Teaching": SegmentType.TEACHING,
            "Practice / Application": SegmentType.PRACTICE,
            "Reflection": SegmentType.REFLECTION,
            "Soft CTA": SegmentType.SOFT_CTA,
            "Calm Closing": SegmentType.CLOSING,
        }

    def run(self, input_data: ScriptWriterInput) -> ScriptWriterOutput:
        """
        เรียบเรียงสคริปต์จากโครงร่างและข้อความอ้างอิง
        """
        try:
            logger.info(f"เริ่มเรียบเรียงสคริปต์สำหรับหัวข้อ: {input_data.outline.topic}")

            # 1. ตรวจสอบข้อมูลเบื้องต้น
            validation_error = self._validate_input_data(input_data)
            if validation_error:
                return self._create_error_response(validation_error)

            # 2. สร้างฐานข้อมูล passages สำหรับ citation
            passage_db = self._build_passage_database(input_data.passages)

            # 3. สร้าง segments จาก outline
            segments = self._generate_segments_from_outline(
                input_data.outline, passage_db, input_data.style_notes
            )

            # 4. เพิ่ม retention cues
            segments = self._add_retention_cues(segments, input_data.target_seconds)

            # 5. คำนวณเวลาและปรับแต่ง
            segments = self._adjust_timing(segments, input_data.target_seconds)

            # 6. ตรวจสอบ citations และสร้างรายการ
            citations_used, unmatched_citations = self._validate_citations(
                segments, passage_db
            )

            # 7. สร้าง metadata
            meta = self._create_meta_info(segments)

            # 8. ตรวจสอบคุณภาพ
            quality_check = self._perform_quality_check(
                segments, citations_used, input_data.target_seconds
            )

            # 9. สร้างคำเตือน
            warnings = self._generate_warnings(quality_check, segments, input_data)

            # 10. สร้างผลลัพธ์
            result = ScriptWriterOutput(
                topic=input_data.outline.topic,
                segments=segments,
                citations_used=citations_used,
                unmatched_citations=unmatched_citations,
                duration_est_total=sum(s.est_seconds for s in segments),
                meta=meta,
                quality_check=quality_check,
                warnings=warnings,
            )

            logger.info(
                f"เรียบเรียงสคริปต์สำเร็จ: {len(segments)} segments, "
                f"{result.duration_est_total} วินาที, "
                f"{len(citations_used)} citations"
            )

            return result

        except Exception as e:
            logger.error(f"เกิดข้อผิดพลาดในการเรียบเรียงสคริปต์: {e}")
            return self._create_error_response(
                {
                    "code": "SCHEMA_VIOLATION",
                    "message": f"เกิดข้อผิดพลาด: {str(e)}",
                    "suggested_fix": "ตรวจสอบข้อมูลนำเข้าและลองใหม่",
                }
            )

    def _validate_input_data(self, input_data: ScriptWriterInput) -> dict | None:
        """ตรวจสอบข้อมูลนำเข้า"""
        if not input_data.outline.outline:
            return {
                "code": "MISSING_DATA",
                "message": "ไม่พบโครงร่างในข้อมูลนำเข้า",
                "suggested_fix": "ตรวจสอบ outline ให้มี sections อย่างน้อย 1 รายการ",
            }

        total_passages = len(input_data.passages.primary) + len(
            input_data.passages.supportive
        )
        if total_passages == 0:
            return {
                "code": "MISSING_DATA",
                "message": "ไม่พบข้อความอ้างอิง passages",
                "suggested_fix": "ตรวจสอบ passages ให้มี primary หรือ supportive อย่างน้อย 1 รายการ",
            }

        return None

    def _create_error_response(self, error_dict: dict) -> ScriptWriterOutput:
        """สร้าง error response ในรูปแบบ ScriptWriterOutput"""
        # สร้าง minimal valid output พร้อมข้อมูลผิดพลาดใน warnings
        error_segment = ScriptSegment(
            segment_type=SegmentType.HOOK,
            text="เกิดข้อผิดพลาดในการเรียบเรียงสคริปต์",
            est_seconds=5,
        )

        return ScriptWriterOutput(
            topic="Error",
            segments=[error_segment],
            citations_used=[],
            unmatched_citations=[],
            duration_est_total=5,
            meta=ScriptMeta(
                reading_speed_wpm=145,
                interrupts_count=0,
                teaching_segments=0,
                practice_steps_count=0,
            ),
            quality_check=QualityCheck(
                citations_valid=False,
                teaching_has_citation=False,
                duration_within_range=False,
                hook_within_8s=False,
                no_prohibited_claims=True,
            ),
            warnings=[
                f"ERROR: {error_dict['message']} - {error_dict['suggested_fix']}"
            ],
        )

    def _build_passage_database(self, passages_data) -> dict[str, any]:
        """สร้างฐานข้อมูล passages สำหรับการอ้างอิง"""
        db = {}

        for passage in passages_data.primary:
            db[passage.id] = passage

        for passage in passages_data.supportive:
            db[passage.id] = passage

        return db

    def _generate_segments_from_outline(
        self, outline, passage_db: dict, style_notes
    ) -> list[ScriptSegment]:
        """สร้าง segments จากโครงร่าง outline"""
        segments = []

        for section in outline.outline:
            segment_type = self._map_section_to_segment_type(section.section)

            # สร้างเนื้อหาตาม segment type
            text = self._generate_segment_content(
                section, segment_type, passage_db, style_notes
            )

            # ประมาณเวลาเบื้องต้น
            est_seconds = self._estimate_segment_duration(text, section.est_seconds)

            segment = ScriptSegment(
                segment_type=segment_type, text=text, est_seconds=est_seconds
            )

            segments.append(segment)

        return segments

    def _map_section_to_segment_type(self, section_name: str) -> SegmentType:
        """แปลงชื่อ section จาก outline เป็น SegmentType"""
        return self.section_to_segment_type.get(section_name, SegmentType.TEACHING)

    def _generate_segment_content(
        self, section, segment_type: SegmentType, passage_db: dict, style_notes
    ) -> str:
        """สร้างเนื้อหา segment ตาม type"""

        if segment_type == SegmentType.HOOK:
            return self._generate_hook_content(section, style_notes)
        elif segment_type == SegmentType.PROBLEM:
            return self._generate_problem_content(section, style_notes)
        elif segment_type == SegmentType.TRANSITION:
            return self._generate_transition_content(section, style_notes)
        elif segment_type == SegmentType.STORY:
            return self._generate_story_content(section, style_notes)
        elif segment_type == SegmentType.TEACHING:
            return self._generate_teaching_content(section, passage_db, style_notes)
        elif segment_type == SegmentType.PRACTICE:
            return self._generate_practice_content(section, passage_db, style_notes)
        elif segment_type == SegmentType.REFLECTION:
            return self._generate_reflection_content(section, style_notes)
        elif segment_type == SegmentType.SOFT_CTA:
            return self._generate_soft_cta_content(section, style_notes)
        elif segment_type == SegmentType.CLOSING:
            return self._generate_closing_content(section, style_notes)
        else:
            return f"เนื้อหาสำหรับ {segment_type.value}"

    def _generate_hook_content(self, section, style_notes) -> str:
        """สร้างเนื้อหา Hook segment"""
        content_draft = getattr(section, "content_draft", "")
        if content_draft:
            return f"{content_draft} เข้าใจไหมครับ?"
        else:
            return "เคยไหมครับที่รู้สึกว่าใจไม่สงบ แม้ว่าแล้วจะอยากพักผ่อน?"

    def _generate_problem_content(self, section, style_notes) -> str:
        """สร้างเนื้อหา Problem segment"""
        key_points = getattr(section, "key_points", [])
        if key_points:
            return (
                f"ปัญหาที่หลายคนพบเจอก็คือ {' '.join(key_points[:2])} ทำให้รู้สึกเหนื่อยและไม่สดชื่น"
            )
        else:
            return "ปัญหาที่หลายคนเจอก็คือ ใจยังคิดวนเวียนแม้จะพยายามพักแล้ว"

    def _generate_transition_content(self, section, style_notes) -> str:
        """สร้างเนื้อหา Transition segment"""
        return "แล้วถ้าเราบอกว่า มีวิธีง่ายๆ ที่ช่วยให้ใจสงบลงได้ล่ะครับ"

    def _generate_story_content(self, section, style_notes) -> str:
        """สร้างเนื้อหา Story segment"""
        analogy_type = getattr(section, "analogy_type", "")
        beat_points = getattr(section, "beat_points", [])

        if analogy_type and beat_points:
            return f"ลองคิดดูเหมือน{analogy_type} {' '.join(beat_points[:2])} นี่แหละครับที่เราจะมาเรียนรู้กัน"
        else:
            return "เหมือนกับน้ำที่ใส เมื่อเราไม่กวนมัน มันก็จะใสและสงบเองครับ"

    def _generate_teaching_content(self, section, passage_db: dict, style_notes) -> str:
        """สร้างเนื้อหา Teaching segment พร้อม citations"""
        content_parts = []

        # ใช้ sub_segments ถ้ามี
        sub_segments = getattr(section, "sub_segments", [])
        if sub_segments:
            for i, sub_segment in enumerate(sub_segments):
                teaching_points = getattr(sub_segment, "teaching_points", [])
                if teaching_points:
                    content_parts.append(f"ขั้นตอนที่ {i + 1}: {teaching_points[0]}")

                    # เพิ่ม citation จาก placeholder ถ้ามี
                    citation_placeholders = getattr(
                        sub_segment, "citation_placeholders", []
                    )
                    if citation_placeholders and citation_placeholders[0] in passage_db:
                        content_parts.append(f"[CIT:{citation_placeholders[0]}]")

        if not content_parts:
            # ถ้าไม่มี sub_segments ให้สร้างเนื้อหาพื้นฐาน
            content_parts.append("หลักการสำคัญก็คือ การรับรู้โดยไม่ยึดติด")

            # พยายามหา passage ที่เกี่ยวข้องเพื่อใส่ citation
            available_passages = list(passage_db.keys())
            if available_passages:
                content_parts.append(f"[CIT:{available_passages[0]}]")

        return " ".join(content_parts)

    def _generate_practice_content(self, section, passage_db: dict, style_notes) -> str:
        """สร้างเนื้อหา Practice segment"""
        steps = getattr(section, "steps", [])
        if steps:
            numbered_steps = [f"{i + 1}. {step}" for i, step in enumerate(steps)]
            return f"ลองปฏิบัติตามนี้ดูครับ: {' '.join(numbered_steps)}"
        else:
            return "ลองหลับตา หายใจเข้าลึกๆ และปล่อยออกช้าๆ สังเกตความรู้สึกที่เกิดขึ้น"

    def _generate_reflection_content(self, section, style_notes) -> str:
        """สร้างเนื้อหา Reflection segment"""
        question = getattr(section, "question", "")
        if question:
            return f"ตอนนี้ลองถามตัวเองว่า {question}"
        else:
            return "รู้สึกอย่างไรบ้างครับ? ใจเริ่มสงบขึ้นหรือเปล่า?"

    def _generate_soft_cta_content(self, section, style_notes) -> str:
        """สร้างเนื้อหา Soft CTA segment"""
        cta_phrase = getattr(section, "cta_phrase", "")
        if cta_phrase:
            return cta_phrase
        else:
            return "ถ้าวิดีโอนี้เป็นประโยชน์ ช่วยกดไลค์และแชร์ให้เพื่อนๆ ด้วยนะครับ"

    def _generate_closing_content(self, section, style_notes) -> str:
        """สร้างเนื้อหา Closing segment"""
        closing_line = getattr(section, "closing_line", "")
        if closing_line:
            return closing_line
        else:
            return "พอแล้วสำหรับวันนี้ ใจค่อยๆ พักได้แล้วครับ"

    def _estimate_segment_duration(self, text: str, outline_est_seconds: int) -> int:
        """ประมาณเวลา segment จากข้อความและค่าจาก outline"""
        # นับคำในข้อความ (ไม่รวม citations และ retention cues)
        clean_text = re.sub(r"\[CIT:[^\]]+\]", "", text)
        clean_text = re.sub(r"\([^)]+\)", "", clean_text)
        word_count = len(clean_text.split())

        # คำนวณเวลาจากจำนวนคำ
        text_based_seconds = int((word_count / self.avg_reading_speed) * 60)

        # ใช้ค่าเฉลี่ยระหว่าง text-based และ outline estimate
        if outline_est_seconds > 0:
            return int((text_based_seconds + outline_est_seconds) / 2)
        else:
            return max(text_based_seconds, 5)  # อย่างน้อย 5 วินาที

    def _add_retention_cues(
        self, segments: list[ScriptSegment], target_seconds: int
    ) -> list[ScriptSegment]:
        """เพิ่ม retention cues ลงใน segments"""
        total_duration = sum(s.est_seconds for s in segments)

        # คำนวณจำนวน cues ที่ต้องการ (ทุกๆ 90-120 วินาที)
        cue_interval = 105  # วินาที
        needed_cues = max(1, total_duration // cue_interval)

        # กระจาย cues ให้เท่าๆ กัน
        cues_added = 0
        for i, segment in enumerate(segments):
            if cues_added < needed_cues and i > 0 and i < len(segments) - 1:
                # เพิ่ม retention cue ที่จุดที่เหมาะสม
                cue = self.retention_cues[cues_added % len(self.retention_cues)]
                segment.text = segment.text + f" {cue}"
                cues_added += 1

        return segments

    def _adjust_timing(
        self, segments: list[ScriptSegment], target_seconds: int
    ) -> list[ScriptSegment]:
        """ปรับเวลา segments ให้ตรงตามเป้าหมาย"""
        current_total = sum(s.est_seconds for s in segments)
        tolerance = target_seconds * 0.15

        if abs(current_total - target_seconds) <= tolerance:
            return segments

        # ถ้าสั้นเกินไป ยืดเวลา teaching และ practice segments
        if current_total < target_seconds * 0.85:
            deficit = target_seconds - current_total
            extendable_segments = [
                s
                for s in segments
                if s.segment_type in [SegmentType.TEACHING, SegmentType.PRACTICE]
            ]

            if extendable_segments:
                extra_per_segment = deficit // len(extendable_segments)
                for segment in extendable_segments:
                    segment.est_seconds += extra_per_segment

        # ถ้ายาวเกินไป ลดเวลา segments ที่ไม่สำคัญ
        elif current_total > target_seconds * 1.15:
            excess = current_total - target_seconds
            reducible_segments = [
                s
                for s in segments
                if s.segment_type not in [SegmentType.HOOK, SegmentType.CLOSING]
            ]

            if reducible_segments:
                reduce_per_segment = min(10, excess // len(reducible_segments))
                for segment in reducible_segments:
                    reduction = min(reduce_per_segment, segment.est_seconds - 5)
                    segment.est_seconds -= reduction

        return segments

    def _validate_citations(
        self, segments: list[ScriptSegment], passage_db: dict
    ) -> tuple[list[str], list[str]]:
        """ตรวจสอบและรวบรวม citations"""
        citations_used = []
        unmatched_citations = []

        # หา citations ทั้งหมดใน segments
        citation_pattern = r"\[CIT:([^\]]+)\]"

        for segment in segments:
            citations = re.findall(citation_pattern, segment.text)
            for citation in citations:
                if citation in passage_db:
                    if citation not in citations_used:
                        citations_used.append(citation)
                else:
                    if citation not in unmatched_citations:
                        unmatched_citations.append(citation)

        return citations_used, unmatched_citations

    def _create_meta_info(self, segments: list[ScriptSegment]) -> ScriptMeta:
        """สร้างข้อมูล metadata"""

        # นับ retention cues
        interrupts_count = 0
        for segment in segments:
            interrupts_count += len(re.findall(r"\([^)]+\)", segment.text))

        # นับ teaching segments
        teaching_segments = sum(
            1 for s in segments if s.segment_type == SegmentType.TEACHING
        )

        # นับขั้นตอน practice
        practice_steps_count = 0
        for segment in segments:
            if segment.segment_type == SegmentType.PRACTICE:
                # นับหมายเลขขั้นตอน
                practice_steps_count += len(re.findall(r"\d+\.", segment.text))

        return ScriptMeta(
            reading_speed_wpm=self.avg_reading_speed,
            interrupts_count=interrupts_count,
            teaching_segments=teaching_segments,
            practice_steps_count=practice_steps_count,
        )

    def _perform_quality_check(
        self,
        segments: list[ScriptSegment],
        citations_used: list[str],
        target_seconds: int,
    ) -> QualityCheck:
        """ตรวจสอบคุณภาพของสคริปต์"""

        # ตรวจสอบ citations
        unmatched_citations = []
        citation_pattern = r"\[CIT:([^\]]+)\]"
        for segment in segments:
            citations = re.findall(citation_pattern, segment.text)
            for citation in citations:
                if citation not in citations_used:
                    unmatched_citations.append(citation)

        citations_valid = len(unmatched_citations) == 0

        # ตรวจสอบ teaching segments มี citation
        teaching_has_citation = False
        for segment in segments:
            if segment.segment_type == SegmentType.TEACHING:
                if "[CIT:" in segment.text:
                    teaching_has_citation = True
                    break

        # ตรวจสอบระยะเวลา
        total_duration = sum(s.est_seconds for s in segments)
        tolerance = target_seconds * 0.15
        duration_within_range = abs(total_duration - target_seconds) <= tolerance

        # ตรวจสอบ hook ไม่เกิน 8 วินาที
        hook_segments = [s for s in segments if s.segment_type == SegmentType.HOOK]
        hook_within_8s = all(s.est_seconds <= 8 for s in hook_segments)

        # ตรวจสอบคำที่ห้ามใช้
        no_prohibited_claims = True
        for segment in segments:
            for claim in self.prohibited_claims:
                if claim in segment.text:
                    no_prohibited_claims = False
                    break

        return QualityCheck(
            citations_valid=citations_valid,
            teaching_has_citation=teaching_has_citation,
            duration_within_range=duration_within_range,
            hook_within_8s=hook_within_8s,
            no_prohibited_claims=no_prohibited_claims,
        )

    def _generate_warnings(
        self,
        quality_check: QualityCheck,
        segments: list[ScriptSegment],
        input_data: ScriptWriterInput,
    ) -> list[str]:
        """สร้างคำเตือนและข้อเสนอแนะ"""
        warnings = []

        if not quality_check.citations_valid:
            warnings.append("พบ citations ที่ไม่ตรงกับ passages ที่ให้มา")

        if not quality_check.teaching_has_citation:
            warnings.append("ส่วน teaching ไม่มี citation อ้างอิง")

        if not quality_check.duration_within_range:
            total_duration = sum(s.est_seconds for s in segments)
            if total_duration < input_data.target_seconds * 0.85:
                diff = input_data.target_seconds - total_duration
                warnings.append(f"สคริปต์สั้นกว่าเป้า {diff} วินาที")
            else:
                diff = total_duration - input_data.target_seconds
                warnings.append(f"สคริปต์ยาวกว่าเป้า {diff} วินาที")

        if not quality_check.hook_within_8s:
            warnings.append("Hook segment เกิน 8 วินาที")

        if not quality_check.no_prohibited_claims:
            warnings.append("พบคำที่อาจสร้างความคาดหวังที่แน่นอนเกินไป")

        # ตรวจสอบจำนวน segments
        if len(segments) < 5:
            warnings.append("จำนวน segments น้อยเกินไป อาจทำให้เนื้อหาไม่สมบูรณ์")

        return warnings
