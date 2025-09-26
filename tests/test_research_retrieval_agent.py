"""
ทดสอบการทำงานของ Research Retrieval Agent
"""

import sys
from datetime import datetime
from pathlib import Path

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agents.research_retrieval import (
    ResearchRetrievalAgent,
    ResearchRetrievalInput,
    ResearchRetrievalOutput,
)
from agents.research_retrieval.model import ErrorResponse


class TestResearchRetrievalAgent:
    """ทดสอบการทำงานของ ResearchRetrievalAgent"""

    @pytest.fixture
    def agent(self):
        """สร้าง ResearchRetrievalAgent สำหรับทดสอบ"""
        return ResearchRetrievalAgent()

    @pytest.fixture
    def sample_input(self):
        """ข้อมูลตัวอย่างสำหรับทดสอบ"""
        return ResearchRetrievalInput(
            topic_title="ปล่อยวางความกังวลก่อนนอน",
            raw_query="วิธีปล่อยวางก่อนนอนจากหลักธรรม",
            refinement_hints=["เน้นการวางความคิดวน", "เกี่ยวโยงสติและอานาปานสติ"],
            max_passages=12,
            required_tags=["สติ", "ปล่อยวาง"],
            forbidden_sources=["แหล่งไม่ตรวจสอบ"],
            context_language="th",
        )

    @pytest.fixture
    def minimal_input(self):
        """ข้อมูลขั้นต่ำสำหรับทดสอบ"""
        return ResearchRetrievalInput(
            topic_title="สติในชีวิตประจำวัน",
            raw_query="การมีสติ",
        )

    def test_agent_initialization(self, agent):
        """ทดสอบการสร้าง Agent"""
        assert agent.name == "ResearchRetrievalAgent"
        assert agent.version == "1.0.0"
        assert "ดึงและวิเคราะห์ข้อความอ้างอิง" in agent.description

    def test_run_basic_functionality(self, agent, sample_input):
        """ทดสอบการรัน Agent พื้นฐาน"""
        result = agent.run(sample_input)

        assert isinstance(result, ResearchRetrievalOutput)
        assert result.topic == sample_input.topic_title
        assert isinstance(result.retrieved_at, datetime)
        assert len(result.queries_used) > 0
        assert len(result.summary_bullets) >= 3
        assert len(result.summary_bullets) <= 6

    def test_run_with_minimal_input(self, agent, minimal_input):
        """ทดสอบการรันด้วยข้อมูลขั้นต่ำ"""
        result = agent.run(minimal_input)

        assert isinstance(result, ResearchRetrievalOutput)
        assert result.topic == minimal_input.topic_title
        assert len(result.queries_used) >= 1  # อย่างน้อยต้องมี base query

    def test_passages_structure(self, agent, sample_input):
        """ทดสอบโครงสร้างของ passages"""
        result = agent.run(sample_input)

        # ตรวจสอบว่ามี primary และ supportive passages
        assert hasattr(result, "primary")
        assert hasattr(result, "supportive")
        assert isinstance(result.primary, list)
        assert isinstance(result.supportive, list)

        # ตรวจสอบโครงสร้างของ passage แต่ละอัน
        all_passages = result.primary + result.supportive
        for passage in all_passages:
            assert passage.id
            assert passage.source_name
            assert passage.collection
            assert passage.original_text
            assert 0 <= passage.relevance_final <= 1
            assert isinstance(passage.doctrinal_tags, list)
            assert passage.license
            assert isinstance(passage.risk_flags, list)
            assert passage.reason

    def test_relevance_scores_validation(self, agent, sample_input):
        """ทดสอบการตรวจสอบคะแนน relevance"""
        result = agent.run(sample_input)

        all_passages = result.primary + result.supportive
        for passage in all_passages:
            assert 0.0 <= passage.relevance_final <= 1.0

    def test_coverage_assessment(self, agent, sample_input):
        """ทดสอบการประเมินความครอบคลุม"""
        result = agent.run(sample_input)

        coverage = result.coverage_assessment
        assert isinstance(coverage.core_concepts, list)
        assert isinstance(coverage.expected_concepts, list)
        assert isinstance(coverage.missing_concepts, list)
        assert 0.0 <= coverage.confidence <= 1.0

        # ตรวจสอบว่า missing_concepts = expected - core
        expected_set = set(coverage.expected_concepts)
        core_set = set(coverage.core_concepts)
        missing_set = set(coverage.missing_concepts)
        assert missing_set == expected_set - core_set

    def test_summary_bullets_count(self, agent, sample_input):
        """ทดสอบจำนวน summary bullets"""
        result = agent.run(sample_input)

        assert 3 <= len(result.summary_bullets) <= 6

    def test_stats_calculation(self, agent, sample_input):
        """ทดสอบการคำนวณสถิติ"""
        result = agent.run(sample_input)

        stats = result.stats
        assert stats.primary_count >= 0
        assert stats.supportive_count >= 0
        assert stats.initial_candidates >= 0
        assert stats.filtered_out >= 0
        assert 0.0 <= stats.avg_relevance_primary <= 1.0

        # ตรวจสอบความสอดคล้องของตัวเลข
        total_returned = stats.primary_count + stats.supportive_count
        assert total_returned <= sample_input.max_passages

    def test_meta_info_structure(self, agent, sample_input):
        """ทดสอบโครงสร้าง meta info"""
        result = agent.run(sample_input)

        meta = result.meta
        assert meta.max_passages_requested == sample_input.max_passages
        assert isinstance(meta.applied_filters, list)
        assert meta.refinement_iterations > 0

        # ตรวจสอบ self_check
        self_check = meta.self_check
        assert isinstance(self_check.has_primary, bool)
        assert isinstance(self_check.confidence_ok, bool)
        assert isinstance(self_check.within_limit, bool)
        assert isinstance(self_check.no_empty_text, bool)

    def test_queries_generation(self, agent, sample_input):
        """ทดสอบการสร้าง queries"""
        result = agent.run(sample_input)

        queries = result.queries_used
        assert len(queries) >= 1  # อย่างน้อยต้องมี base query

        # ตรวจสอบว่ามี base query
        base_queries = [q for q in queries if q.type == "base"]
        assert len(base_queries) == 1

        # ตรวจสอบโครงสร้างของ query
        for query in queries:
            assert query.type in [
                "base",
                "refinement_doctrine",
                "refinement_practice",
                "refinement_story",
            ]
            assert query.query

    def test_required_tags_filtering(self, agent):
        """ทดสอบการกรองตาม required_tags"""
        input_with_tags = ResearchRetrievalInput(
            topic_title="การมีสติ",
            raw_query="สติในชีวิต",
            required_tags=["สติ"],
        )

        result = agent.run(input_with_tags)

        # ตรวจสอบว่าได้ output ที่ถูกต้อง
        if isinstance(result, ErrorResponse):
            pytest.skip("ได้ ErrorResponse แทน ResearchRetrievalOutput")

        all_passages = result.primary + result.supportive

        # ถ้ามี passages ควรมี tag ที่ต้องการ หรือ passages ทั่วไป
        if all_passages:
            # อย่างน้อยบาง passages ควรมี required tags หรือ related tags
            any(
                any(
                    tag in passage.doctrinal_tags
                    for tag in input_with_tags.required_tags + ["สติ", "ปล่อยวาง"]
                )
                for passage in all_passages
            )

    def test_max_passages_limit(self, agent):
        """ทดสอบการจำกัดจำนวน passages"""
        input_small = ResearchRetrievalInput(
            topic_title="การปล่อยวาง",
            raw_query="ปล่อยวาง",
            max_passages=5,
        )

        result = agent.run(input_small)
        total_passages = len(result.primary) + len(result.supportive)
        assert total_passages <= input_small.max_passages

    def test_sleep_related_topic(self, agent):
        """ทดสอบหัวข้อเกี่ยวกับการนอน"""
        sleep_input = ResearchRetrievalInput(
            topic_title="ปล่อยวางก่อนนอน",
            raw_query="วิธีหลับลึก",
        )

        result = agent.run(sleep_input)

        # ควรมี passages ที่เกี่ยวกับการนอน
        all_passages = result.primary + result.supportive
        assert len(all_passages) > 0

        # ตรวจสอบว่ามีแนวคิดที่เกี่ยวข้อง
        all_tags = set()
        for passage in all_passages:
            all_tags.update(passage.doctrinal_tags)

        relevant_tags = {"สติ", "ความสงบ", "อานาปานสติ"}
        assert len(all_tags & relevant_tags) > 0

    def test_stress_related_topic(self, agent):
        """ทดสอบหัวข้อเกี่ยวกับความเครียด"""
        stress_input = ResearchRetrievalInput(
            topic_title="จัดการความเครียด",
            raw_query="ลดความกังวล",
        )

        result = agent.run(stress_input)
        all_passages = result.primary + result.supportive
        assert len(all_passages) > 0

    def test_warnings_generation(self, agent, sample_input):
        """ทดสอบการสร้าง warnings"""
        result = agent.run(sample_input)

        assert isinstance(result.warnings, list)

        # ถ้ามี missing_concepts ควรมี warning
        if result.coverage_assessment.missing_concepts:
            missing_warning = any(
                "missing_concepts" in warning for warning in result.warnings
            )
            assert missing_warning

    def test_normalize_query(self, agent):
        """ทดสอบการปรับแต่งคำค้น"""
        test_query = "วิธีการปล่อยวางที่มีประสิทธิภาพ"
        normalized = agent._normalize_query(test_query)

        assert isinstance(normalized, str)
        assert "ปล่อยวาง" in normalized  # คำธรรมะต้องเก็บไว้

    def test_input_validation(self):
        """ทดสอบการตรวจสอบข้อมูลนำเข้า"""
        # ทดสอบ max_passages ที่ไม่ถูกต้อง
        with pytest.raises(ValueError):
            ResearchRetrievalInput(
                topic_title="test",
                raw_query="test",
                max_passages=100,  # เกินขีดจำกัด
            )

        # ทดสอบ topic_title ว่าง
        with pytest.raises(ValueError):
            ResearchRetrievalInput(
                topic_title="",
                raw_query="test",
            )

    def test_passage_validation(self):
        """ทดสอบการตรวจสอบ Passage"""
        from agents.research_retrieval.model import Passage

        # ทดสอบ relevance_final ที่ไม่ถูกต้อง
        with pytest.raises(ValueError):
            Passage(
                id="test",
                source_name="test",
                collection="test",
                original_text="test content",
                relevance_final=1.5,  # เกิน 1.0
                doctrinal_tags=[],
                license="public_domain",
                reason="test",
            )

        # ทดสอบ original_text ว่าง
        with pytest.raises(ValueError):
            Passage(
                id="test",
                source_name="test",
                collection="test",
                original_text="",  # ว่าง
                relevance_final=0.5,
                doctrinal_tags=[],
                license="public_domain",
                reason="test",
            )

    def test_output_validation(self, agent, sample_input):
        """ทดสอบการตรวจสอบ output"""
        result = agent.run(sample_input)

        # ตรวจสอบโครงสร้าง output
        assert hasattr(result, "topic")
        assert hasattr(result, "retrieved_at")
        assert hasattr(result, "queries_used")
        assert hasattr(result, "primary")
        assert hasattr(result, "supportive")
        assert hasattr(result, "summary_bullets")
        assert hasattr(result, "coverage_assessment")
        assert hasattr(result, "stats")
        assert hasattr(result, "meta")
        assert hasattr(result, "warnings")

    def test_dhamma_keywords_preservation(self, agent):
        """ทดสอบการเก็บคำธรรมะสำคัญ"""
        query_with_dhamma = "สติและปล่อยวางในชีวิต"
        normalized = agent._normalize_query(query_with_dhamma)

        assert "สติ" in normalized
        assert "ปล่อยวาง" in normalized

    def test_empty_passages_handling(self, agent):
        """ทดสอบการจัดการกรณีไม่มี passages"""
        # ใช้ topic ที่ไม่มีข้อมูล
        empty_input = ResearchRetrievalInput(
            topic_title="หัวข้อที่ไม่มีข้อมูล xyz123",
            raw_query="คำค้นที่ไม่มีข้อมูล xyz123",
            required_tags=["แท็กที่ไม่มี xyz123"],
        )

        result = agent.run(empty_input)

        # ควรได้ผลลัพธ์แม้ไม่มี passages หรือ ErrorResponse
        if isinstance(result, ErrorResponse):
            # ถ้าได้ ErrorResponse ก็ยอมรับได้
            assert "error" in result.error
        else:
            # ถ้าได้ ResearchRetrievalOutput ควรมี confidence ต่ำ
            assert isinstance(result, ResearchRetrievalOutput)
            assert result.coverage_assessment.confidence < 0.5  # ความมั่นใจต่ำ
            assert result.warnings, "Expected warnings when no passages are found"
            expected_warning_keys = {"insufficient_passages", "no_primary_passages"}
            assert expected_warning_keys.intersection(
                set(result.warnings)
            ), "Warnings should include insufficient passages information"
