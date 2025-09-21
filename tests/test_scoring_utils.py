"""
ทดสอบฟังก์ชันการคำนวณคะแนนและการจัดอันดับ
ตรวจสอบ utils.scoring module
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from automation_core.utils.scoring import (
    calculate_composite_score,
    normalize_scores,
    rank_items_by_score,
    validate_score_range,
)


class TestCalculateCompositeScore:
    """ทดสอบการคำนวณคะแนนรวม"""

    def test_basic_composite_calculation(self):
        """ทดสอบการคำนวณพื้นฐาน"""
        scores = {
            "search_intent": 0.8,
            "freshness": 0.6,
            "evergreen": 0.7,
            "brand_fit": 0.9
        }
        weights = {
            "search_intent": 0.3,
            "freshness": 0.25,
            "evergreen": 0.25,
            "brand_fit": 0.2
        }

        result = calculate_composite_score(scores, weights)

        # คำนวณค่าที่คาดหวัง
        expected = (0.8 * 0.3 + 0.6 * 0.25 + 0.7 * 0.25 + 0.9 * 0.2)

        assert abs(result - expected) < 0.001
        assert 0 <= result <= 1

    def test_equal_weights(self):
        """ทดสอบเมื่อน้ำหนักเท่ากัน"""
        scores = {"a": 0.6, "b": 0.8, "c": 0.4}
        weights = {"a": 1.0, "b": 1.0, "c": 1.0}

        result = calculate_composite_score(scores, weights)
        expected = (0.6 + 0.8 + 0.4) / 3

        assert abs(result - expected) < 0.001

    def test_missing_score_key(self):
        """ทดสอบเมื่อมี key ใน weights แต่ไม่มีใน scores"""
        scores = {"a": 0.7, "b": 0.5}
        weights = {"a": 0.5, "b": 0.3, "c": 0.2}  # c ไม่มีใน scores

        result = calculate_composite_score(scores, weights)
        expected = (0.7 * 0.5 + 0.5 * 0.3) / (0.5 + 0.3)

        assert abs(result - expected) < 0.001

    def test_zero_weights(self):
        """ทดสอบเมื่อน้ำหนักรวมเป็นศูนย์"""
        scores = {"a": 0.8, "b": 0.6}
        weights = {"c": 0.5, "d": 0.3}  # ไม่มี key ตรงกัน

        result = calculate_composite_score(scores, weights)
        assert result == 0.0

    def test_trend_scout_weights(self):
        """ทดสอบด้วยน้ำหนักของ TrendScoutAgent"""
        scores = {
            "search_intent": 0.82,
            "freshness": 0.74,
            "evergreen": 0.65,
            "brand_fit": 0.93
        }
        weights = {
            "search_intent": 0.30,
            "freshness": 0.25,
            "evergreen": 0.25,
            "brand_fit": 0.20
        }

        result = calculate_composite_score(scores, weights)
        expected = 0.82 * 0.3 + 0.74 * 0.25 + 0.65 * 0.25 + 0.93 * 0.2

        assert abs(result - expected) < 0.001
        assert 0 <= result <= 1


class TestNormalizeScores:
    """ทดสอบการปรับคะแนนให้อยู่ในช่วงที่กำหนด"""

    def test_basic_normalization(self):
        """ทดสอบการปรับคะแนนพื้นฐาน"""
        scores = [10, 20, 30, 40, 50]

        result = normalize_scores(scores, 0.0, 1.0)

        # ตรวจสอบช่วงค่า
        assert all(0.0 <= score <= 1.0 for score in result)

        # ค่าต่ำสุดควรเป็น 0, ค่าสูงสุดควรเป็น 1
        assert result[0] == 0.0  # 10 (ต่ำสุด)
        assert result[-1] == 1.0  # 50 (สูงสุด)

        # ควรเรียงลำดับเดิม
        assert result == sorted(result)

    def test_custom_range(self):
        """ทดสอบการใช้ช่วงค่าที่กำหนดเอง"""
        scores = [1, 2, 3, 4, 5]

        result = normalize_scores(scores, 0.2, 0.8)

        # ตรวจสอบช่วงค่า
        assert all(0.2 <= score <= 0.8 for score in result)

        # ค่าต่ำสุดและสูงสุด
        assert result[0] == 0.2
        assert result[-1] == 0.8

    def test_identical_scores(self):
        """ทดสอบเมื่อคะแนนทุกตัวเท่ากัน"""
        scores = [5, 5, 5, 5]

        result = normalize_scores(scores, 0.0, 1.0)

        # ทุกค่าควรเป็น min_val เนื่องจากไม่มีการกระจาย
        assert all(score == 0.0 for score in result)

    def test_empty_list(self):
        """ทดสอบเมื่อรายการว่าง"""
        result = normalize_scores([], 0.0, 1.0)
        assert result == []

    def test_single_score(self):
        """ทดสอบเมื่อมีคะแนนเดียว"""
        result = normalize_scores([42], 0.0, 1.0)
        assert result == [0.0]  # ค่าเดียวจะกลายเป็น min_val


class TestRankItemsByScore:
    """ทดสอบการจัดอันดับรายการ"""

    def test_basic_ranking(self):
        """ทดสอบการจัดอันดับพื้นฐาน"""
        items = [
            {"name": "A", "score": 0.7},
            {"name": "B", "score": 0.9},
            {"name": "C", "score": 0.5}
        ]

        result = rank_items_by_score(items, "score")

        # ตรวจสอบการเรียงลำดับ (สูงไปต่ำ)
        assert result[0]["name"] == "B"  # คะแนนสูงสุด
        assert result[1]["name"] == "A"
        assert result[2]["name"] == "C"  # คะแนนต่ำสุด

        # ตรวจสอบ rank
        assert result[0]["rank"] == 1
        assert result[1]["rank"] == 2
        assert result[2]["rank"] == 3

    def test_reverse_ranking(self):
        """ทดสอบการจัดอันดับจากต่ำไปสูง"""
        items = [
            {"name": "A", "value": 100},
            {"name": "B", "value": 50},
            {"name": "C", "value": 200}
        ]

        result = rank_items_by_score(items, "value", reverse=False)

        # ตรวจสอบการเรียงลำดับ (ต่ำไปสูง)
        assert result[0]["name"] == "B"  # ค่าต่ำสุด
        assert result[1]["name"] == "A"
        assert result[2]["name"] == "C"  # ค่าสูงสุด

    def test_empty_list(self):
        """ทดสอบเมื่อรายการว่าง"""
        result = rank_items_by_score([], "score")
        assert result == []

    def test_missing_score_key(self):
        """ทดสอบเมื่อ item บางตัวไม่มี score key"""
        items = [
            {"name": "A", "score": 0.8},
            {"name": "B"},  # ไม่มี score
            {"name": "C", "score": 0.6}
        ]

        result = rank_items_by_score(items, "score")

        # item ที่ไม่มี score จะได้ค่า default 0
        scores = [item.get("score", 0) for item in result]
        assert scores == sorted(scores, reverse=True)

    def test_composite_score_ranking(self):
        """ทดสอบการจัดอันดับด้วยคะแนนรวม (เหมือน TrendScout)"""
        items = [
            {"title": "หัวข้อ A", "composite": 0.785},
            {"title": "หัวข้อ B", "composite": 0.892},
            {"title": "หัวข้อ C", "composite": 0.634}
        ]

        result = rank_items_by_score(items, "composite")

        # ตรวจสอบลำดับ
        assert result[0]["title"] == "หัวข้อ B"
        assert result[1]["title"] == "หัวข้อ A"
        assert result[2]["title"] == "หัวข้อ C"

        # ตรวจสอบ rank
        for i, item in enumerate(result, 1):
            assert item["rank"] == i


class TestValidateScoreRange:
    """ทดสอบการตรวจสอบช่วงค่าคะแนน"""

    def test_valid_scores(self):
        """ทดสอบคะแนนที่ถูกต้อง"""
        scores = {
            "search_intent": 0.8,
            "freshness": 0.0,
            "evergreen": 1.0,
            "brand_fit": 0.5
        }

        result = validate_score_range(scores, 0.0, 1.0)
        assert result is True

    def test_invalid_scores_above_max(self):
        """ทดสอบคะแนนเกินค่าสูงสุด"""
        scores = {
            "search_intent": 0.8,
            "freshness": 1.2,  # เกิน 1.0
            "evergreen": 0.5
        }

        result = validate_score_range(scores, 0.0, 1.0)
        assert result is False

    def test_invalid_scores_below_min(self):
        """ทดสอบคะแนนต่ำกว่าค่าต่ำสุด"""
        scores = {
            "search_intent": 0.8,
            "freshness": -0.1,  # ต่ำกว่า 0.0
            "evergreen": 0.5
        }

        result = validate_score_range(scores, 0.0, 1.0)
        assert result is False

    def test_non_numeric_scores(self):
        """ทดสอบคะแนนที่ไม่ใช่ตัวเลข"""
        scores = {
            "search_intent": 0.8,
            "freshness": "high",  # ไม่ใช่ตัวเลข
            "evergreen": 0.5
        }

        result = validate_score_range(scores, 0.0, 1.0)
        assert result is False

    def test_custom_range(self):
        """ทดสอบการใช้ช่วงค่าที่กำหนดเอง"""
        scores = {
            "score1": 5,
            "score2": 10,
            "score3": 7
        }

        result = validate_score_range(scores, 0, 10)
        assert result is True

        result = validate_score_range(scores, 6, 10)
        assert result is False  # score1 = 5 ต่ำกว่า min

    def test_empty_scores(self):
        """ทดสอบเมื่อไม่มีคะแนน"""
        result = validate_score_range({}, 0.0, 1.0)
        assert result is True  # ไม่มีคะแนนให้ตรวจสอบ


class TestScoringIntegration:
    """ทดสอบการทำงานร่วมกันของฟังก์ชันต่างๆ"""

    def test_full_scoring_workflow(self):
        """ทดสอบขั้นตอนการให้คะแนนแบบเต็ม"""
        # ข้อมูลหัวข้อตัวอย่าง
        raw_scores = [
            {"search": 0.8, "fresh": 0.6, "evergreen": 0.7, "brand": 0.9},
            {"search": 0.6, "fresh": 0.9, "evergreen": 0.5, "brand": 0.7},
            {"search": 0.9, "fresh": 0.4, "evergreen": 0.8, "brand": 0.8}
        ]

        weights = {"search": 0.3, "fresh": 0.25, "evergreen": 0.25, "brand": 0.2}

        # คำนวณคะแนนรวมและสร้าง items
        items = []
        for i, scores in enumerate(raw_scores):
            composite = calculate_composite_score(scores, weights)
            items.append({
                "id": i,
                "title": f"หัวข้อ {i+1}",
                "composite": composite,
                "scores": scores
            })

        # จัดอันดับ
        ranked_items = rank_items_by_score(items, "composite")

        # ตรวจสอบผลลัพธ์
        assert len(ranked_items) == 3
        assert all(item["rank"] >= 1 for item in ranked_items)

        # ตรวจสอบการเรียงลำดับ
        composite_scores = [item["composite"] for item in ranked_items]
        assert composite_scores == sorted(composite_scores, reverse=True)

        # ตรวจสอบช่วงค่าคะแนน
        all_scores = {}
        for item in ranked_items:
            for key, value in item["scores"].items():
                all_scores[f"{item['id']}_{key}"] = value
            all_scores[f"{item['id']}_composite"] = item["composite"]

        assert validate_score_range(all_scores, 0.0, 1.0)
