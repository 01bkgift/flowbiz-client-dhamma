"""
automation_core - โมดูลหลักสำหรับระบบ Dhamma Automation

ประกอบด้วย:
- BaseAgent: คลาสพื้นฐานสำหรับ AI Agents ทั้งหมด
- Config: การจัดการ configuration
- Logging: ระบบ logging
- PromptLoader: โหลด prompt templates
- Utils: ฟังก์ชันช่วยเหลือต่างๆ
"""

__version__ = "0.1.0"
__author__ = "Dhamma Automation Team"

from .base_agent import BaseAgent
from .config import AppConfig
from .logging import setup_logging
from .prompt_loader import PromptLoadError, load_prompt

__all__ = [
    "BaseAgent",
    "AppConfig",
    "setup_logging",
    "load_prompt",
    "PromptLoadError",
]
