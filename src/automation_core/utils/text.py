"""
ฟังก์ชันสำหรับการประมวลผลข้อความ
"""

import re


def clean_text(text: str) -> str:
    """
    ทำความสะอาดข้อความ - ลบช่องว่างเกิน, ตัวอักษรพิเศษ
    
    Args:
        text: ข้อความที่ต้องการทำความสะอาด
        
    Returns:
        ข้อความที่ทำความสะอาดแล้ว
    """

    if not text:
        return ""

    # ลบช่องว่างเกินและขึ้นบรรทัดใหม่เกิน
    text = re.sub(r'\s+', ' ', text.strip())

    # ลบอักขระควบคุมที่ไม่ต้องการ
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x84\x86-\x9f]', '', text)

    return text


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """
    ตัดข้อความให้มีความยาวไม่เกินที่กำหนด
    
    Args:
        text: ข้อความต้นฉบับ
        max_length: ความยาวสูงสุด
        suffix: ข้อความต่อท้าย (ถ้าตัด)
        
    Returns:
        ข้อความที่ตัดแล้ว
    """

    if not text or max_length <= 0:
        return ""

    if len(text) <= max_length:
        return text

    # ตัดข้อความ โดยเหลือที่ว่างสำหรับ suffix
    actual_length = max_length - len(suffix)
    if actual_length <= 0:
        return suffix[:max_length]

    return text[:actual_length] + suffix


def extract_keywords(text: str) -> list[str]:
    """
    แยกคำสำคัญจากข้อความ (ง่ายๆ ด้วยการแยกคำ)
    
    Args:
        text: ข้อความที่ต้องการแยกคำ
        
    Returns:
        รายการคำสำคัญ
    """

    if not text:
        return []

    # ทำความสะอาดข้อความ
    clean = clean_text(text.lower())

    # แยกคำด้วย whitespace และเครื่องหมายวรรคตอน
    words = re.findall(r'\b\w+\b', clean)

    # กรองคำที่สั้นเกินไป
    keywords = [word for word in words if len(word) >= 2]

    # ลบคำซ้ำ แต่รักษาลำดับ
    seen = set()
    unique_keywords = []
    for keyword in keywords:
        if keyword not in seen:
            seen.add(keyword)
            unique_keywords.append(keyword)

    return unique_keywords


def is_thai_text(text: str, threshold: float = 0.5) -> bool:
    """
    ตรวจสอบว่าข้อความเป็นภาษาไทยหรือไม่
    
    Args:
        text: ข้อความที่ต้องการตรวจสอบ
        threshold: สัดส่วนต่ำสุดของอักขระไทย (0.0 - 1.0)
        
    Returns:
        True ถ้าเป็นภาษาไทย
    """

    if not text:
        return False

    # นับอักขระไทย (U+0E00 - U+0E7F)
    thai_chars = sum(1 for char in text if '\u0E00' <= char <= '\u0E7F')

    # นับอักขระที่ไม่ใช่ whitespace
    non_space_chars = sum(1 for char in text if not char.isspace())

    if non_space_chars == 0:
        return False

    # คำนวณสัดส่วน
    thai_ratio = thai_chars / non_space_chars

    return thai_ratio >= threshold


def create_youtube_title(
    base_text: str,
    max_length: int = 60,
    keywords: list[str] | None = None
) -> str:
    """
    สร้างชื่อวิดีโอ YouTube ที่เหมาะสม
    
    Args:
        base_text: ข้อความพื้นฐาน
        max_length: ความยาวสูงสุด (YouTube แนะนำ 60 ตัวอักษร)
        keywords: คำสำคัญที่ต้องการใส่
        
    Returns:
        ชื่อวิดีโอที่ปรับแต่งแล้ว
    """

    # ทำความสะอาดข้อความ
    title = clean_text(base_text)

    # ถ้าข้อความสั้นกว่าที่กำหนด และมี keywords ให้เพิ่ม
    if keywords and len(title) < max_length - 10:
        # เลือก keyword ที่ยังไม่มีในชื่อ
        missing_keywords = [kw for kw in keywords if kw.lower() not in title.lower()]

        if missing_keywords:
            # เพิ่ม keyword แรกที่หาได้
            keyword = missing_keywords[0]
            potential_title = f"{title} {keyword}"

            if len(potential_title) <= max_length:
                title = potential_title

    # ตัดให้พอดีความยาว
    title = truncate_text(title, max_length, "...")

    # ลบช่องว่างเกินที่อาจเกิดขึ้น
    title = clean_text(title)

    return title
