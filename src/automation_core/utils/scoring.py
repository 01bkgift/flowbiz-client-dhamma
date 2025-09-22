"""
ฟังก์ชันสำหรับการคำนวณคะแนนและการจัดอันดับ
"""

from typing import Any

import numpy as np


def calculate_composite_score(
    scores: dict[str, float], weights: dict[str, float]
) -> float:
    """
    คำนวณคะแนนรวม (composite score) จากคะแนนย่อยและน้ำหนัก

    Args:
        scores: Dictionary ของคะแนนย่อย
        weights: Dictionary ของน้ำหนักสำหรับแต่ละคะแนน

    Returns:
        คะแนนรวมที่คำนวณได้

    Example:
        >>> scores = {"search_intent": 0.8, "freshness": 0.6}
        >>> weights = {"search_intent": 0.5, "freshness": 0.5}
        >>> calculate_composite_score(scores, weights)
        0.7
    """

    total_weighted_score = 0.0
    total_weights = 0.0

    for key, weight in weights.items():
        if key in scores:
            total_weighted_score += scores[key] * weight
            total_weights += weight

    # ป้องกันการหารด้วยศูนย์
    if total_weights == 0:
        return 0.0

    return total_weighted_score / total_weights


def normalize_scores(
    scores: list[float], min_val: float = 0.0, max_val: float = 1.0
) -> list[float]:
    """
    ปรับคะแนนให้อยู่ในช่วงที่กำหนด (normalization)

    Args:
        scores: รายการคะแนนที่ต้องการปรับ
        min_val: ค่าต่ำสุดที่ต้องการ
        max_val: ค่าสูงสุดที่ต้องการ

    Returns:
        รายการคะแนนที่ปรับแล้ว
    """

    if not scores:
        return []

    scores_array = np.array(scores)

    # หาค่าต่ำสุดและสูงสุดในข้อมูล
    current_min = scores_array.min()
    current_max = scores_array.max()

    # ถ้าค่าทุกตัวเท่ากัน
    if current_max == current_min:
        return [min_val] * len(scores)

    # ปรับขนาดให้อยู่ในช่วงใหม่
    normalized = (scores_array - current_min) / (current_max - current_min)
    normalized = normalized * (max_val - min_val) + min_val

    return normalized.tolist()


def rank_items_by_score(
    items: list[dict[str, Any]], score_key: str = "composite", reverse: bool = True
) -> list[dict[str, Any]]:
    """
    จัดอันดับรายการตามคะแนน

    Args:
        items: รายการที่ต้องการจัดอันดับ
        score_key: key ของคะแนนที่ใช้จัดอันดับ
        reverse: True = สูงไปต่ำ, False = ต่ำไปสูง

    Returns:
        รายการที่จัดอันดับแล้ว พร้อมเพิ่ม rank
    """

    if not items:
        return []

    # จัดเรียงตามคะแนน
    sorted_items = sorted(items, key=lambda x: x.get(score_key, 0), reverse=reverse)

    # เพิ่ม rank
    for i, item in enumerate(sorted_items, 1):
        item["rank"] = i

    return sorted_items


def validate_score_range(
    scores: dict[str, float], min_val: float = 0.0, max_val: float = 1.0
) -> bool:
    """
    ตรวจสอบว่าคะแนนทั้งหมดอยู่ในช่วงที่ถูกต้อง

    Args:
        scores: Dictionary ของคะแนน
        min_val: ค่าต่ำสุดที่ยอมรับได้
        max_val: ค่าสูงสุดที่ยอมรับได้

    Returns:
        True ถ้าคะแนนทั้งหมดอยู่ในช่วงที่ถูกต้อง
    """

    for score in scores.values():
        if not isinstance(score, int | float):
            return False
        if score < min_val or score > max_val:
            return False

    return True
