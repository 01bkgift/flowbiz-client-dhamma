"""Test cases สำหรับ DoctrineValidatorAgent"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agents.doctrine_validator.agent import DoctrineValidatorAgent
from agents.doctrine_validator.model import (
    DoctrineValidatorInput,
    DoctrineValidatorOutput,
    ErrorResponse,
    Passage,
    Passages,
    ScriptSegment,
    SegmentStatus,
)


class TestDoctrineValidatorAgent:
    """ชุดทดสอบสำหรับ DoctrineValidatorAgent"""

    def setup_method(self):
        self.agent = DoctrineValidatorAgent()
        self.base_passages = Passages(
            primary=[
                Passage(
                    id="p123",
                    original_text="การมีสติรู้ลมหายใจเข้าออกช่วยให้ใจสงบ",
                    thai_modernized="การมีสติอยู่กับลมหายใจทำให้ใจสงบ",
                    doctrinal_tags=["สติ"],
                    canonical_ref="MN 118",
                    license="public_domain",
                )
            ],
            supportive=[
                Passage(
                    id="p210",
                    original_text="การปล่อยวางความคิดช่วยให้ใจคลาย",
                    thai_modernized="วางความคิดทำให้ใจผ่อนคลาย",
                    doctrinal_tags=["ปล่อยวาง"],
                    canonical_ref="SN 36",
                    license="restricted",
                )
            ],
        )

    def test_agent_initialization(self):
        assert self.agent.name == "DoctrineValidatorAgent"
        assert "doctrinal" in self.agent.description

    def test_basic_validation_ok(self):
        segments = [
            ScriptSegment(
                segment_type="teaching",
                text="การมีสติรู้ลมหายใจเข้าออกช่วยให้ใจสงบ [CIT:p123]",
                est_seconds=60,
            )
        ]

        input_data = DoctrineValidatorInput(
            script_segments=segments,
            passages=self.base_passages,
            strictness="normal",
        )

        result = self.agent.run(input_data)

        assert isinstance(result, DoctrineValidatorOutput)
        assert result.summary.total == 1
        assert result.summary.ok == 1
        assert result.segments[0].status == SegmentStatus.OK
        assert result.segments[0].matched_passages == ["p123"]

    def test_missing_citation_and_sensitive_detection(self):
        segments = [
            ScriptSegment(
                segment_type="teaching",
                text="การหายใจเข้าออกอย่างมีสติช่วยให้ใจสงบ [CIT:p123]",
                est_seconds=60,
            ),
            ScriptSegment(
                segment_type="teaching",
                text="สมาธิรักษาโรคและหายป่วยแน่นอน",
                est_seconds=50,
            ),
            ScriptSegment(
                segment_type="practice",
                text="เพียงตั้งใจหายใจ สมาธิรักษาโรค",
                est_seconds=40,
            ),
        ]

        input_data = DoctrineValidatorInput(
            script_segments=segments,
            passages=self.base_passages,
            strictness="normal",
            check_sensitive=True,
        )

        result = self.agent.run(input_data)
        statuses = [segment.status for segment in result.segments]

        assert statuses[1] == SegmentStatus.HALLUCINATION
        assert statuses[2] == SegmentStatus.UNVERIFIABLE
        assert any("สุ่มเสี่ยง" in warn for warn in result.segments[2].warnings)
        assert result.summary.hallucination == 1
        assert result.summary.missing_citation == 0
        assert result.summary.unverifiable >= 1
        assert result.summary.total == 3

    def test_unmatched_citation_sets_unverifiable(self):
        segments = [
            ScriptSegment(
                segment_type="teaching",
                text="การเจริญเมตตาช่วยให้ใจอ่อนโยน [CIT:p999]",
                est_seconds=55,
            )
        ]

        input_data = DoctrineValidatorInput(
            script_segments=segments,
            passages=self.base_passages,
            strictness="normal",
        )

        result = self.agent.run(input_data)

        assert result.segments[0].status == SegmentStatus.UNVERIFIABLE
        assert any("ไม่พบ" in warn for warn in result.segments[0].warnings)
        assert result.summary.unverifiable == 1

    def test_strict_mode_flags_non_public_license(self):
        segments = [
            ScriptSegment(
                segment_type="teaching",
                text="การวางใจต่อความคิดทำให้ใจคลาย [CIT:p210]",
                est_seconds=45,
            )
        ]

        input_data = DoctrineValidatorInput(
            script_segments=segments,
            passages=self.base_passages,
            strictness="strict",
        )

        result = self.agent.run(input_data)

        assert any("license" in warn for warn in result.segments[0].warnings)
        assert result.segments[0].matched_passages == ["p210"]

    def test_ignore_segments(self):
        segments = [
            ScriptSegment(
                segment_type="teaching",
                text="การหายใจเข้าออกอย่างมีสติช่วยให้ใจสงบ [CIT:p123]",
                est_seconds=60,
            ),
            ScriptSegment(
                segment_type="teaching",
                text="ควรตรวจสอบเพิ่มเติม",
                est_seconds=30,
            ),
        ]

        input_data = DoctrineValidatorInput(
            script_segments=segments,
            passages=self.base_passages,
            strictness="normal",
            ignore_segments=[1],
        )

        result = self.agent.run(input_data)

        assert result.summary.total == 1
        assert all(segment.index != 1 for segment in result.segments)

    def test_error_when_all_segments_ignored(self):
        segments = [
            ScriptSegment(
                segment_type="teaching",
                text="การหายใจเข้าออกอย่างมีสติช่วยให้ใจสงบ [CIT:p123]",
                est_seconds=60,
            )
        ]

        input_data = DoctrineValidatorInput(
            script_segments=segments,
            passages=self.base_passages,
            strictness="normal",
            ignore_segments=[0],
        )

        result = self.agent.run(input_data)

        assert isinstance(result, ErrorResponse)
        assert result.error["code"] == "MISSING_DATA"
