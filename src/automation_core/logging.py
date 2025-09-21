"""
ระบบ Logging ด้วย Rich Console และไฟล์
รองรับการแสดงผลสวยงามและบันทึกลงไฟล์
"""

import logging
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler
from rich.traceback import install

from .config import config


def setup_logging(
    log_level: str | None = None,
    log_file: str | None = None,
    enable_rich_traceback: bool = True
) -> logging.Logger:
    """
    ตั้งค่าระบบ logging สำหรับแอปพลิเคชัน
    
    Args:
        log_level: ระดับการ log (DEBUG, INFO, WARNING, ERROR)
        log_file: ไฟล์สำหรับบันทึก log
        enable_rich_traceback: เปิดใช้ Rich traceback
        
    Returns:
        Logger object ที่ตั้งค่าแล้ว
    """

    # ใช้ค่าจาก config หากไม่ได้ระบุ
    log_level = log_level or config.log_level
    log_file = log_file or config.log_file

    # ติดตั้ง Rich traceback
    if enable_rich_traceback:
        install(show_locals=True)

    # สร้าง console สำหรับ Rich
    console = Console()

    # ตั้งค่า root logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper()))

    # เคลียร์ handlers เดิม
    logger.handlers.clear()

    # Handler สำหรับ console (Rich)
    console_handler = RichHandler(
        console=console,
        show_time=True,
        show_path=True,
        markup=True,
        rich_tracebacks=True
    )
    console_handler.setLevel(getattr(logging, log_level.upper()))

    # Format สำหรับ console
    console_format = "%(message)s"
    console_formatter = logging.Formatter(console_format)
    console_handler.setFormatter(console_formatter)

    logger.addHandler(console_handler)

    # Handler สำหรับไฟล์ (ถ้าระบุ)
    if log_file:
        # สร้างโฟลเดอร์หากไม่มี
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)  # เก็บทุกระดับในไฟล์

        # Format สำหรับไฟล์ (รายละเอียดมากกว่า)
        file_format = "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
        file_formatter = logging.Formatter(file_format)
        file_handler.setFormatter(file_formatter)

        logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    สร้าง logger สำหรับโมดูลเฉพาะ
    
    Args:
        name: ชื่อ logger (ปกติใช้ __name__)
        
    Returns:
        Logger object
    """
    return logging.getLogger(name)


# ตั้งค่า logger หลักเมื่อ import โมดูล
main_logger = setup_logging()
