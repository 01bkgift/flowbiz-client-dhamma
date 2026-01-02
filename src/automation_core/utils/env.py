"""
ฟังก์ชันสำหรับการจัดการค่าจากตัวแปรสภาพแวดล้อม
"""


def parse_pipeline_enabled(env_value: str | None) -> bool:
    """
    แปลงค่าจากตัวแปรสภาพแวดล้อมที่ใช้ควบคุมการเปิด/ปิด pipeline ให้เป็นค่า boolean

    Args:
        env_value: ค่าจากตัวแปรสภาพแวดล้อม PIPELINE_ENABLED หรือ None
            ถ้าเป็น None จะถือว่า pipeline เปิดใช้งานอยู่

    Returns:
        bool: True ถ้า pipeline ถือว่าเปิดใช้งาน
              False ถ้าค่าเป็นหนึ่งใน ("false", "0", "no", "off", "disabled")
              (ไม่คำนึงถึงตัวพิมพ์ใหญ่/เล็ก และตัดช่องว่างรอบข้างแล้ว)
    """
    if env_value is None:
        return True
    return env_value.strip().lower() not in ("false", "0", "no", "off", "disabled")
