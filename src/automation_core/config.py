"""
การตั้งค่าแอปพลิเคชันด้วย Pydantic Settings
รองรับการโหลดจากไฟล์ .env และ environment variables
"""


from pydantic import Field
from pydantic_settings import BaseSettings


class AppConfig(BaseSettings):
    """การตั้งค่าหลักของแอปพลิเคชัน"""

    app_name: str = Field(default="dhamma-automation", description="ชื่อแอปพลิเคชัน")
    log_level: str = Field(default="INFO", description="ระดับการ log")
    data_dir: str = Field(default="./data", description="โฟลเดอร์เก็บข้อมูล")

    # Logging settings
    log_file: str = Field(default="logs/app.log", description="ไฟล์ log")
    log_rotation_size: str = Field(default="10MB", description="ขนาดไฟล์ log ก่อนหมุนเวียน")
    log_retention_days: int = Field(default=30, description="จำนวนวันเก็บ log")

    # API Keys (สำหรับอนาคต)
    openai_api_key: str | None = Field(default=None, description="OpenAI API Key")
    youtube_api_key: str | None = Field(default=None, description="YouTube API Key")
    google_trends_api_key: str | None = Field(default=None, description="Google Trends API Key")

    # Database (สำหรับอนาคต)
    database_url: str | None = Field(default=None, description="Database URL")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# สร้าง instance เดียวสำหรับใช้ทั่วทั้งแอป
config = AppConfig()
