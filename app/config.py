import os

from dotenv import load_dotenv

load_dotenv()

APP_NAME = os.getenv("APP_NAME", "dhamma-automation")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-me")
SESSION_COOKIE = os.getenv("SESSION_COOKIE_NAME", "dhamma_session")

# บัญชีผู้ดูแลระบบ (ไม่มีระบบสมัครสมาชิก)
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

# ไดเรกทอรีข้อมูล/เอาต์พุต (ใช้ของโปรเจกต์เดิม)
DATA_DIR = os.getenv("DATA_DIR", "./data")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "./output")

# ตั้งค่า LLM/API (ไม่บังคับในเว็บนี้)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# ตัวเรียก Python สำหรับ CLI (ช่วยให้ Windows กำหนดได้แม่นยำ)
PYTHON_BIN = os.getenv("PYTHON_BIN", "")
