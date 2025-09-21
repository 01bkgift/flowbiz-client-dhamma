"""
ทดสอบ TrendScoutAgent
ตรวจสอบการทำงานของ Agent และรูปแบบผลลัพธ์
"""

import json
import sys
from datetime import datetime
from pathlib import Path

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agents.trend_scout import TrendScoutAgent, TrendScoutInput, TrendScoutOutput
from agents.trend_scout.model import CompetitorComment, GoogleTrendItem, YTTrendingItem


class TestTrendScoutAgent:
    """ทดสอบการทำงานของ TrendScoutAgent"""

    @pytest.fixture
    def sample_input(self):
        """ข้อมูลตัวอย่างสำหรับทดสอบ"""
        return TrendScoutInput(
            keywords=["ปล่อยวาง", "นอนไม่หลับ", "เครียด"],
            google_trends=[
                GoogleTrendItem(
                    term="ปล่อยวาง",
                    score_series=[54, 60, 67, 72, 75],
                    region="TH"
                ),
                GoogleTrendItem(
                    term="เครียด",
                    score_series=[78, 82, 79, 85, 88],
                    region="TH"
                )
            ],
            youtube_trending_raw=[
                YTTrendingItem(
                    title="นอนยังไงให้ใจหยุดฟุ้ง",
                    views_est=230000,
                    age_days=2,
                    keywords=["นอน", "ฟุ้งซ่าน"]
                ),
                YTTrendingItem(
                    title="วิธีรับมือความเครียด",
                    views_est=180000,
                    age_days=5,
                    keywords=["เครียด", "รับมือ"]
                )
            ],
            competitor_comments=[
                CompetitorComment(
                    channel="คู่เทียบA",
                    comment="เครียดนอนไม่หลับทำยังไง",
                    likes=12
                )
            ]
        )

    @pytest.fixture
    def agent(self):
        """สร้าง TrendScoutAgent สำหรับทดสอบ"""
        return TrendScoutAgent()

    def test_agent_initialization(self, agent):
        """ทดสอบการสร้าง Agent"""
        assert agent.name == "TrendScoutAgent"
        assert agent.version == "1.0.0"
        assert "วิเคราะห์เทรนด์" in agent.description

        # ตรวจสอบน้ำหนักคะแนน
        assert agent.score_weights["search_intent"] == 0.30
        assert agent.score_weights["freshness"] == 0.25
        assert agent.score_weights["evergreen"] == 0.25
        assert agent.score_weights["brand_fit"] == 0.20

        # ตรวจสอบ content pillars
        assert "ธรรมะประยุกต์" in agent.content_pillars
        assert "การทำสมาธิ" in agent.content_pillars

    def test_run_basic_functionality(self, agent, sample_input):
        """ทดสอบการรัน Agent พื้นฐาน"""
        result = agent.run(sample_input)

        # ตรวจสอบประเภทของผลลัพธ์
        assert isinstance(result, TrendScoutOutput)

        # ตรวจสอบ fields หลัก
        assert hasattr(result, 'generated_at')
        assert hasattr(result, 'topics')
        assert hasattr(result, 'meta')

        # ตรวจสอบเวลาที่สร้าง
        assert isinstance(result.generated_at, datetime)

        # ตรวจสอบว่ามี topics
        assert len(result.topics) > 0
        assert len(result.topics) <= 15  # ไม่เกิน 15 หัวข้อ

    def test_topics_structure(self, agent, sample_input):
        """ทดสอบโครงสร้างของหัวข้อ"""
        result = agent.run(sample_input)

        for topic in result.topics:
            # ตรวจสอบ fields หลัก
            assert hasattr(topic, 'rank')
            assert hasattr(topic, 'title')
            assert hasattr(topic, 'pillar')
            assert hasattr(topic, 'predicted_14d_views')
            assert hasattr(topic, 'scores')
            assert hasattr(topic, 'reason')
            assert hasattr(topic, 'raw_keywords')

            # ตรวจสอบประเภทข้อมูล
            assert isinstance(topic.rank, int)
            assert isinstance(topic.title, str)
            assert isinstance(topic.predicted_14d_views, int)
            assert isinstance(topic.raw_keywords, list)

            # ตรวจสอบค่าที่ถูกต้อง
            assert topic.rank >= 1
            assert len(topic.title) > 0
            assert len(topic.title) <= 60  # ความยาวชื่อไม่เกิน 60 ตัวอักษร
            assert topic.predicted_14d_views >= 0

    def test_score_validation(self, agent, sample_input):
        """ทดสอบการตรวจสอบคะแนน"""
        result = agent.run(sample_input)

        for topic in result.topics:
            scores = topic.scores

            # ตรวจสอบว่าคะแนนทั้งหมดอยู่ในช่วง [0, 1]
            assert 0.0 <= scores.search_intent <= 1.0
            assert 0.0 <= scores.freshness <= 1.0
            assert 0.0 <= scores.evergreen <= 1.0
            assert 0.0 <= scores.brand_fit <= 1.0
            assert 0.0 <= scores.composite <= 1.0

    def test_topics_sorted_by_composite_score(self, agent, sample_input):
        """ทดสอบการเรียงลำดับตามคะแนนรวม"""
        result = agent.run(sample_input)

        if len(result.topics) > 1:
            scores = [topic.scores.composite for topic in result.topics]

            # ตรวจสอบว่าเรียงจากมากไปน้อย
            assert scores == sorted(scores, reverse=True)

            # ตรวจสอบ rank ต่อเนื่อง
            for i, topic in enumerate(result.topics, 1):
                assert topic.rank == i

    def test_meta_information(self, agent, sample_input):
        """ทดสอบข้อมูล metadata"""
        result = agent.run(sample_input)
        meta = result.meta

        # ตรวจสอบ fields หลัก
        assert hasattr(meta, 'total_candidates_considered')
        assert hasattr(meta, 'prediction_method')
        assert hasattr(meta, 'self_check')

        # ตรวจสอบค่า
        assert meta.total_candidates_considered > 0
        assert isinstance(meta.prediction_method, str)
        assert len(meta.prediction_method) > 0

        # ตรวจสอบ self_check
        assert hasattr(meta.self_check, 'duplicate_ok')
        assert hasattr(meta.self_check, 'score_range_valid')
        assert isinstance(meta.self_check.duplicate_ok, bool)
        assert isinstance(meta.self_check.score_range_valid, bool)

    def test_content_pillars_assignment(self, agent, sample_input):
        """ทดสอบการกำหนด content pillar"""
        result = agent.run(sample_input)

        for topic in result.topics:
            # ตรวจสอบว่า pillar อยู่ในรายการที่กำหนด
            assert topic.pillar in agent.content_pillars

    def test_empty_input_handling(self, agent):
        """ทดสอบการจัดการกับข้อมูลที่ว่าง"""
        empty_input = TrendScoutInput(keywords=["test"])

        result = agent.run(empty_input)

        # ควรยังสร้างผลลัพธ์ได้
        assert isinstance(result, TrendScoutOutput)
        assert len(result.topics) > 0

    def test_deterministic_output(self, agent, sample_input):
        """ทดสอบความสม่ำเสมอของผลลัพธ์"""
        # รันหลายครั้งกับข้อมูลเดียวกัน
        result1 = agent.run(sample_input)
        result2 = agent.run(sample_input)

        # ผลลัพธ์ควรเหมือนกัน (deterministic)
        assert len(result1.topics) == len(result2.topics)

        for topic1, topic2 in zip(result1.topics, result2.topics, strict=False):
            assert topic1.title == topic2.title
            assert topic1.scores.composite == topic2.scores.composite

    def test_keyword_utilization(self, agent, sample_input):
        """ทดสอบการใช้คำสำคัญ"""
        result = agent.run(sample_input)

        input_keywords = set(sample_input.keywords)

        # ตรวจสอบว่ามีการใช้คำสำคัญในผลลัพธ์
        used_keywords = set()
        for topic in result.topics:
            used_keywords.update(topic.raw_keywords)

        # ควรมีคำสำคัญจาก input บางส่วน
        assert len(input_keywords.intersection(used_keywords)) > 0


class TestTrendScoutWithMockData:
    """ทดสอบกับข้อมูล mock จริง"""

    def test_with_mock_input_file(self):
        """ทดสอบกับไฟล์ mock_input.json"""
        # หา path ของไฟล์ mock
        mock_file = Path("src/agents/trend_scout/mock_input.json")

        if mock_file.exists():
            # โหลดข้อมูล
            with open(mock_file, encoding='utf-8') as f:
                mock_data = json.load(f)

            # แปลงเป็น Input model
            input_data = TrendScoutInput(**mock_data)

            # รัน Agent
            agent = TrendScoutAgent()
            result = agent.run(input_data)

            # ตรวจสอบผลลัพธ์
            assert len(result.topics) > 0
            assert result.meta.self_check.score_range_valid
            assert result.meta.self_check.duplicate_ok
