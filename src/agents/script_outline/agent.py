"""
ScriptOutlineAgent - Agent สำหรับสร้างโครงร่างวิดีโอ

Agent นี้สร้างโครงร่างวิดีโอที่มีโครงสร้างชัดเจน พร้อมการคำนวณเวลา
และการจัดวาง retention patterns ตามมาตรฐานของช่อง YouTube ธรรมะดีดี
"""

import hashlib
import logging

from automation_core.base_agent import BaseAgent

from .model import (
    ConceptCoverage,
    CoreTeachingSubSegment,
    MetaInfo,
    OutlineSection,
    PacingCheck,
    ScriptOutlineInput,
    ScriptOutlineOutput,
    SelfCheck,
)

logger = logging.getLogger(__name__)


class ScriptOutlineAgent(BaseAgent[ScriptOutlineInput, ScriptOutlineOutput]):
    """
    Agent สำหรับสร้างโครงร่างวิดีโอ

    วิธีการทำงาน:
    1. วิเคราะห์หัวข้อและผู้ชมเป้าหมาย
    2. เลือก hook pattern ที่เหมาะสม
    3. สร้างโครงร่างตามโครงสร้างมาตรฐาน
    4. คำนวณเวลาและจัดวาง retention patterns
    5. ตรวจสอบการครอบคลุมแนวคิดและจังหวะ
    """

    def __init__(self):
        super().__init__(
            name="ScriptOutlineAgent",
            version="1.0.0",
            description="สร้างโครงร่างวิดีโอ Long-form สำหรับช่อง YouTube ธรรมะดีดี",
        )

        # Hook patterns ที่ใช้ได้
        self.hook_patterns = {
            "question_open": "เคยไหม…?",
            "contrast_mini": "ทั้งเหนื่อยแต่ใจยังไม่พัก?",
            "micro_story": "เมื่อคืนตีสอง คุณยังพลิกตัว…",
            "sensory_invoke": "เสียงแอร์ยังดังแต่ใจยังคิดเรื่องเดิม…",
            "data_hint": "กว่า 60% ของคนทำงาน…",
        }

        # Retention pattern tags ที่ใช้ได้
        self.retention_patterns = [
            "pattern_interrupt",
            "guided_breath",
            "rhetorical_question",
            "analogy_shift",
            "soft_pause",
            "recap_bridge",
            "emotional_labeling",
        ]

        # ส่วนโครงสร้างมาตรฐาน
        self.standard_sections = [
            "Hook",
            "Problem Amplify",
            "Transition Prompt",
            "Story / Analogy",
            "Core Teaching",
            "Practice / Application",
            "Reflection Question",
            "Soft CTA",
            "Calm Closing",
        ]

    def run(self, input_data: ScriptOutlineInput) -> ScriptOutlineOutput:
        """
        สร้างโครงร่างวิดีโอจากข้อมูลที่ได้รับ
        """
        logger.info(f"เริ่มสร้างโครงร่างสำหรับ: {input_data.topic_title}")

        try:
            # 1. เลือก hook pattern
            hook_pattern = self._select_hook_pattern(input_data)
            logger.debug(f"เลือก hook pattern: {hook_pattern}")

            # 2. สร้างโครงร่างแต่ละส่วน
            outline = self._create_outline_sections(input_data, hook_pattern)
            logger.debug(f"สร้างโครงร่างได้ {len(outline)} ส่วน")

            # 3. คำนวณและตรวจสอบเวลา
            pacing_check = self._calculate_pacing_check(
                outline, input_data.target_minutes
            )

            # 4. ตรวจสอบการครอบคลุมแนวคิด
            concept_coverage = self._check_concept_coverage(outline, input_data)

            # 5. สร้าง hook variants
            hook_variants = self._generate_hook_variants(input_data, hook_pattern)

            # 6. สร้าง metadata
            meta_info = self._create_meta_info(outline, hook_pattern, pacing_check)

            # 7. สร้างคำเตือน
            warnings = self._generate_warnings(pacing_check, concept_coverage)

            # 8. สร้างผลลัพธ์
            result = ScriptOutlineOutput(
                topic=input_data.topic_title,
                duration_target_min=input_data.target_minutes,
                outline=outline,
                pacing_check=pacing_check,
                concept_coverage=concept_coverage,
                hook_variants=hook_variants,
                meta=meta_info,
                warnings=warnings,
            )

            logger.info(
                f"สร้างโครงร่างสำเร็จ เวลารวม {pacing_check.total_est_seconds} วินาที"
            )
            return result

        except Exception as e:
            logger.error(f"เกิดข้อผิดพลาดในการสร้างโครงร่าง: {e}")
            raise

    def _select_hook_pattern(self, input_data: ScriptOutlineInput) -> str:
        """เลือก hook pattern ที่เหมาะสมกับหัวข้อ"""

        # ใช้ hash ของหัวข้อเพื่อเลือกแบบ deterministic
        topic_hash = int(hashlib.md5(input_data.topic_title.encode()).hexdigest(), 16)
        pattern_keys = list(self.hook_patterns.keys())
        selected_idx = topic_hash % len(pattern_keys)

        return pattern_keys[selected_idx]

    def _create_outline_sections(
        self, input_data: ScriptOutlineInput, hook_pattern: str
    ) -> list[OutlineSection]:
        """สร้างส่วนต่างๆ ของโครงร่าง"""

        sections = []

        # 1. Hook
        hook_section = self._create_hook_section(input_data, hook_pattern)
        sections.append(hook_section)

        # 2. Problem Amplify
        problem_section = self._create_problem_amplify_section(input_data)
        sections.append(problem_section)

        # 3. Story / Analogy (optional, 80% chance)
        if self._should_include_story(input_data):
            story_section = self._create_story_section(input_data)
            sections.append(story_section)

        # 4. Core Teaching
        core_section = self._create_core_teaching_section(input_data)
        sections.append(core_section)

        # 5. Practice / Application
        practice_section = self._create_practice_section(input_data)
        sections.append(practice_section)

        # 6. Reflection Question
        reflection_section = self._create_reflection_section(input_data)
        sections.append(reflection_section)

        # 7. Soft CTA
        cta_section = self._create_cta_section(input_data)
        sections.append(cta_section)

        # 8. Calm Closing (optional)
        if self._should_include_closing(input_data):
            closing_section = self._create_closing_section(input_data)
            sections.append(closing_section)

        return sections

    def _create_hook_section(
        self, input_data: ScriptOutlineInput, hook_pattern: str
    ) -> OutlineSection:
        """สร้างส่วน Hook"""

        # สร้างเนื้อหา hook ตาม pattern
        content_draft = self._generate_hook_content(input_data, hook_pattern)

        return OutlineSection(
            section="Hook",
            hook_pattern=hook_pattern,
            goal="ดึงให้ผู้ชมรู้สึกถูกเข้าใจ",
            est_seconds=7,
            content_draft=content_draft,
            retention_tags=["rhetorical_question"],
        )

    def _create_problem_amplify_section(
        self, input_data: ScriptOutlineInput
    ) -> OutlineSection:
        """สร้างส่วน Problem Amplify"""

        # สร้างประเด็นปัญหาจาก pain points
        key_points = []
        for pain_point in input_data.viewer_persona.pain_points[:3]:
            # แปลง pain point เป็นประเด็นที่ขยายความ
            point = self._expand_pain_point(pain_point)
            key_points.append(point)

        return OutlineSection(
            section="Problem Amplify",
            goal="ขยายอาการ + ภาวะใจ",
            est_seconds=50,
            key_points=key_points,
            retention_tags=["emotional_labeling", "pattern_interrupt"],
        )

    def _create_story_section(self, input_data: ScriptOutlineInput) -> OutlineSection:
        """สร้างส่วน Story / Analogy"""

        # เลือกภาพเปรียบจากหัวข้อ
        analogy_type, beat_points = self._select_analogy(input_data.topic_title)

        return OutlineSection(
            section="Story / Analogy",
            est_seconds=80,
            analogy_type=analogy_type,
            beat_points=beat_points,
            retention_tags=["analogy_shift"],
        )

    def _create_core_teaching_section(
        self, input_data: ScriptOutlineInput
    ) -> OutlineSection:
        """สร้างส่วน Core Teaching"""

        # สร้าง sub-segments จาก core concepts
        sub_segments = []
        concepts_to_use = input_data.core_concepts[:3]  # ใช้สูงสุด 3 concepts

        for i, concept in enumerate(concepts_to_use):
            sub_segment = self._create_teaching_sub_segment(concept, i)
            sub_segments.append(sub_segment)

        # คำนวณเวลารวม
        total_seconds = sum(segment.est_seconds for segment in sub_segments)

        return OutlineSection(
            section="Core Teaching",
            est_seconds=total_seconds,
            sub_segments=sub_segments,
            retention_tags=["guided_breath", "soft_pause"],
        )

    def _create_practice_section(
        self, input_data: ScriptOutlineInput
    ) -> OutlineSection:
        """สร้างส่วน Practice / Application"""

        # สร้างขั้นตอนปฏิบัติ 4-5 ข้อ
        steps = self._generate_practice_steps(input_data)

        return OutlineSection(
            section="Practice / Application",
            est_seconds=75,
            steps=steps,
            retention_tags=["recap_bridge"],
        )

    def _create_reflection_section(
        self, input_data: ScriptOutlineInput
    ) -> OutlineSection:
        """สร้างส่วน Reflection Question"""

        question = self._generate_reflection_question(input_data)

        return OutlineSection(
            section="Reflection Question",
            est_seconds=15,
            question=question,
            retention_tags=["rhetorical_question", "soft_pause"],
        )

    def _create_cta_section(self, input_data: ScriptOutlineInput) -> OutlineSection:
        """สร้างส่วน Soft CTA"""

        cta_phrase = "ถ้าคลิปนี้ช่วยให้ใจคุณเบาลง ฝากกดติดตาม แล้วลองทำอีกครั้งนะครับ"

        return OutlineSection(
            section="Soft CTA",
            est_seconds=18,
            cta_phrase=cta_phrase,
            retention_tags=[],
        )

    def _create_closing_section(self, input_data: ScriptOutlineInput) -> OutlineSection:
        """สร้างส่วน Calm Closing"""

        closing_line = "พอแล้วสำหรับวันนี้ ใจค่อยๆ พักได้"

        return OutlineSection(
            section="Calm Closing",
            est_seconds=10,
            closing_line=closing_line,
            retention_tags=["soft_pause"],
        )

    def _should_include_story(self, input_data: ScriptOutlineInput) -> bool:
        """ตัดสินใจว่าควรใส่ story/analogy หรือไม่"""
        # ใช้ hash เพื่อความสม่ำเสมอ
        topic_hash = hash(input_data.topic_title) % 100
        return topic_hash < 80  # 80% โอกาส

    def _should_include_closing(self, input_data: ScriptOutlineInput) -> bool:
        """ตัดสินใจว่าควรใส่ calm closing หรือไม่"""
        # ใส่เสมอสำหรับหัวข้อเกี่ยวกับการพักผ่อน/นอนหลับ
        sleep_keywords = ["นอน", "หลับ", "พัก", "ผ่อนคลาย", "สงบ"]
        return any(keyword in input_data.topic_title for keyword in sleep_keywords)

    def _generate_hook_content(
        self, input_data: ScriptOutlineInput, pattern: str
    ) -> str:
        """สร้างเนื้อหา hook ตาม pattern"""

        if pattern == "question_open":
            return f"เคยไหม {input_data.viewer_persona.pain_points[0]}?"
        elif pattern == "contrast_mini":
            return f"ทั้ง{input_data.viewer_persona.pain_points[0]}แต่{input_data.viewer_persona.pain_points[1] if len(input_data.viewer_persona.pain_points) > 1 else 'ใจยังไม่สงบ'}?"
        elif pattern == "micro_story":
            return f"เมื่อคืนคุณ{input_data.viewer_persona.pain_points[0]}…"
        elif pattern == "sensory_invoke":
            return f"เสียงรอบตัวยังดัง แต่{input_data.viewer_persona.pain_points[0]}…"
        else:  # data_hint
            return f"กว่า 60% ของ{input_data.viewer_persona.name} {input_data.viewer_persona.pain_points[0]}"

    def _expand_pain_point(self, pain_point: str) -> str:
        """ขยายความจาก pain point เป็นประเด็นปัญหา"""
        expansions = {
            "นอนไม่ค่อยหลับ": "ร่างกายเหนื่อยแต่ความคิดยังตึง",
            "คิดเรื่องงานซ้ำ": "ยิ่งพยายามหยุดคิดยิ่งคิดมาก",
            "กังวลอนาคต": "คิดถึงผลลัพธ์พรุ่งนี้ → ใจยิ่งไม่พัก",
        }
        return expansions.get(pain_point, f"ปัญหา{pain_point}ที่หลายคนพบ")

    def _select_analogy(self, topic_title: str) -> tuple[str, list[str]]:
        """เลือกภาพเปรียบที่เหมาะสม"""

        analogies = {
            "ปล่อยวาง": (
                "ปล่อยหินในน้ำ",
                [
                    "กุมก้อนหินแน่น = ความคิด",
                    "แรงกดมือเริ่มเจ็บ = ใจเหนื่อย",
                    "ปล่อยให้ตก = คลายการยึด",
                ],
            ),
            "สติ": (
                "แสงไฟฉายในป่า",
                [
                    "ป่าในความมืด = ความคิดยุ่งเหยิง",
                    "ไฟฉายส่องทาง = สติ",
                    "เห็นทางเดินชัด = ใจสงบ",
                ],
            ),
            "กังวล": (
                "คลื่นในทะเล",
                ["คลื่นลูกใหญ่ = ความกังวล", "พายุผ่านไป = อารมณ์เปลี่ยน", "ทะเลสงบ = ใจที่แท้จริง"],
            ),
        }

        # หาคำสำคัญในหัวข้อ
        for key, (analogy_type, beat_points) in analogies.items():
            if key in topic_title:
                return analogy_type, beat_points

        # ค่าเริ่มต้น
        return analogies["ปล่อยวาง"]

    def _create_teaching_sub_segment(
        self, concept: str, index: int
    ) -> CoreTeachingSubSegment:
        """สร้าง sub-segment สำหรับการสอน"""

        teaching_content = {
            "สติ": {
                "label": "การรับรู้สติ",
                "points": ["สังเกตลมหายใจเข้าออก", "รู้เมื่อใจไปคิดเรื่องอื่น"],
                "concepts": ["สติ", "สมาธิ"],
            },
            "เวทนา": {
                "label": "การรับรู้เวทนา",
                "points": ["สังเกตความตึงบริเวณหน้าอก/หน้าผาก", "ไม่ต้องผลักความคิด แค่รู้ว่ามี"],
                "concepts": ["เวทนา", "สติ"],
            },
            "ปล่อยวาง": {
                "label": "การปล่อยวาง",
                "points": ["ยอมรับสิ่งที่เกิดขึ้น", "ไม่บังคับให้เป็นไปตามใจ"],
                "concepts": ["ปล่อยวาง", "อุปาทาน"],
            },
            "อานาปานสติ": {
                "label": "อานาปานสติสั้น",
                "points": ["ตามลมหายใจ 5 รอบโดยไม่ปรับ", "รับรู้ความกว้างของใจหลังลมรอบที่ 5"],
                "concepts": ["อานาปานสติ", "ปล่อยวาง"],
            },
        }

        content = teaching_content.get(
            concept,
            {
                "label": f"การเข้าใจ{concept}",
                "points": [f"หลักการของ{concept}", f"การประยุกต์{concept}ในชีวิต"],
                "concepts": [concept],
            },
        )

        return CoreTeachingSubSegment(
            label=content["label"],
            est_seconds=80 + (index * 10),  # ปรับเวลาตามลำดับ
            teaching_points=content["points"],
            concept_links=content["concepts"],
            citation_placeholders=[f"p{123 + index * 100}"],
            retention_tags=(
                ["guided_breath"] if "อานาปาน" in concept else ["soft_pause"]
            ),
        )

    def _generate_practice_steps(self, input_data: ScriptOutlineInput) -> list[str]:
        """สร้างขั้นตอนการปฏิบัติ"""

        base_steps = [
            "หาที่นั่งสบาย หรือนอนในท่าที่ผ่อนคลาย",
            "หลับตาเบาๆ และรู้เวทนากาย 10–15 วินาที",
            "ตามลมหายใจธรรมชาติ 5 รอบ",
            "สังเกตความคิดที่เหลือ แล้วปล่อยวาง",
        ]

        # ปรับให้เข้ากับ desired_state
        if "หลับ" in input_data.viewer_persona.desired_state:
            base_steps.insert(0, "วางมือถือให้พ้นสายตา")
            base_steps.append("บอกตัวเอง 'พรุ่งนี้ค่อยจัดการ' แล้วปล่อยใจให้พัก")

        return base_steps

    def _generate_reflection_question(self, input_data: ScriptOutlineInput) -> str:
        """สร้างคำถาม reflection"""

        questions = [
            "ถ้าความคิดพรุ่งนี้ยังไม่จบวันนี้ได้ คุณยังอยากกุมมันไว้ทั้งคืนไหม?",
            "ใจที่ผ่อนคลายกับใจที่ตึงเครียด ใจแบบไหนที่คุณอยากอยู่ด้วย?",
            "ถ้าเราไม่สามารถควบคุมความคิดได้ เราจะปล่อยวางยังไง?",
        ]

        # เลือกตาม hash
        topic_hash = hash(input_data.topic_title) % len(questions)
        return questions[topic_hash]

    def _calculate_pacing_check(
        self, outline: list[OutlineSection], target_minutes: int
    ) -> PacingCheck:
        """คำนวณและตรวจสอบจังหวะเวลา"""

        total_seconds = sum(section.est_seconds for section in outline)
        target_seconds = target_minutes * 60
        tolerance = 0.15  # ±15%

        min_seconds = int(target_seconds * (1 - tolerance))
        max_seconds = int(target_seconds * (1 + tolerance))
        within_range = min_seconds <= total_seconds <= max_seconds

        # สร้างความคิดเห็น
        if total_seconds < min_seconds:
            comment = f"ต่ำกว่าเป้าประมาณ {min_seconds - total_seconds} วินาที ควรขยาย Core Teaching หรือ Practice"
        elif total_seconds > max_seconds:
            comment = (
                f"เกินเป้าประมาณ {total_seconds - max_seconds} วินาที ควรลดเวลาในบางส่วน"
            )
        else:
            comment = "อยู่ในช่วงเป้าหมายที่เหมาะสม"

        return PacingCheck(
            total_est_seconds=total_seconds,
            within_range=within_range,
            target_range_seconds=[min_seconds, max_seconds],
            comment=comment,
        )

    def _check_concept_coverage(
        self, outline: list[OutlineSection], input_data: ScriptOutlineInput
    ) -> ConceptCoverage:
        """ตรวจสอบการครอบคลุมแนวคิด"""

        expected_concepts = input_data.core_concepts + input_data.missing_concepts
        covered_concepts = set()

        # หาแนวคิดที่ครอบคลุมแล้วจากโครงร่าง
        for section in outline:
            if section.sub_segments:
                for sub_segment in section.sub_segments:
                    covered_concepts.update(sub_segment.concept_links)

        covered_list = list(covered_concepts.intersection(expected_concepts))
        missing_list = [
            concept for concept in expected_concepts if concept not in covered_concepts
        ]

        # แนะนำส่วนที่ควรเพิ่ม
        suggest_section = None
        if missing_list:
            if any("เมตตา" in concept for concept in missing_list):
                suggest_section = "Reflection Question หรือ Calm Closing"
            else:
                suggest_section = "Core Teaching"

        coverage_ratio = (
            len(covered_list) / len(expected_concepts) if expected_concepts else 1.0
        )

        return ConceptCoverage(
            expected=expected_concepts,
            covered=covered_list,
            missing=missing_list,
            suggest_add_in_section=suggest_section,
            coverage_ratio=coverage_ratio,
        )

    def _generate_hook_variants(
        self, input_data: ScriptOutlineInput, selected_pattern: str
    ) -> list[str]:
        """สร้าง hook variants อื่นๆ"""

        variants = []

        # สร้าง variants จาก patterns อื่นที่ไม่ได้เลือก
        other_patterns = [p for p in self.hook_patterns.keys() if p != selected_pattern]

        for pattern in other_patterns[:2]:  # เลือกแค่ 2 อันแรก
            content = self._generate_hook_content(input_data, pattern)
            variants.append(content)

        return variants

    def _create_meta_info(
        self,
        outline: list[OutlineSection],
        hook_pattern: str,
        pacing_check: PacingCheck,
    ) -> MetaInfo:
        """สร้างข้อมูล metadata"""

        # รวม retention patterns ที่ใช้
        all_retention_patterns = set()
        for section in outline:
            all_retention_patterns.update(section.retention_tags)

        # ตรวจสอบ interrupt spacing (ทุก 120 วินาที)
        interrupt_spacing_ok = self._check_interrupt_spacing(outline)

        # ตรวจสอบด้วยตัวเอง
        self_check = SelfCheck(
            time_within_tolerance=pacing_check.within_range,
            has_core_sections=any(s.section == "Core Teaching" for s in outline),
            no_empty_sections=all(s.est_seconds > 0 for s in outline),
        )

        return MetaInfo(
            hook_pattern_selected=hook_pattern,
            retention_patterns_used=list(all_retention_patterns),
            interrupt_spacing_ok=interrupt_spacing_ok,
            self_check=self_check,
        )

    def _check_interrupt_spacing(self, outline: list[OutlineSection]) -> bool:
        """ตรวจสอบการจัดช่วงเวลา interrupt patterns"""

        cumulative_time = 0
        last_interrupt_time = 0

        interrupt_patterns = ["pattern_interrupt", "guided_breath", "analogy_shift"]

        for section in outline:
            cumulative_time += section.est_seconds

            # ตรวจสอบว่ามี interrupt pattern หรือไม่
            has_interrupt = any(
                pattern in section.retention_tags for pattern in interrupt_patterns
            )

            # ถ้าผ่านไป 120 วินาทีแล้วยังไม่มี interrupt
            if cumulative_time - last_interrupt_time > 120 and not has_interrupt:
                return False

            if has_interrupt:
                last_interrupt_time = cumulative_time

        return True

    def _generate_warnings(
        self, pacing_check: PacingCheck, concept_coverage: ConceptCoverage
    ) -> list[str]:
        """สร้างคำเตือน"""

        warnings = []

        if not pacing_check.within_range:
            if pacing_check.total_est_seconds < pacing_check.target_range_seconds[0]:
                diff = (
                    pacing_check.target_range_seconds[0]
                    - pacing_check.total_est_seconds
                )
                warnings.append(f"ระยะเวลารวมต่ำกว่าเป้าประมาณ {diff} วินาที")
            else:
                diff = (
                    pacing_check.total_est_seconds
                    - pacing_check.target_range_seconds[1]
                )
                warnings.append(f"ระยะเวลารวมเกินเป้าประมาณ {diff} วินาที")

        if concept_coverage.missing:
            for concept in concept_coverage.missing:
                warnings.append(f"missing concept: {concept}")

        return warnings
