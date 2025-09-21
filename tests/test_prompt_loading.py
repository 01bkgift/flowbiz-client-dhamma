"""
ทดสอบระบบการโหลด Prompt Templates
ตรวจสอบการทำงานของ prompt_loader module
"""

import sys
import tempfile
from pathlib import Path

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from automation_core.prompt_loader import PromptLoadError, get_prompt_path, load_prompt


class TestPromptLoader:
    """ทดสอบการโหลด prompt templates"""

    def test_load_prompt_success(self):
        """ทดสอบการโหลด prompt สำเร็จ"""
        # สร้างไฟล์ชั่วคราว
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            test_content = "คุณคือ AI Assistant ที่ช่วยเหลือผู้ใช้\nตอบคำถามด้วยความสุภาพ"
            f.write(test_content)
            temp_path = f.name

        try:
            # โหลด prompt
            content = load_prompt(temp_path)

            # ตรวจสอบผลลัพธ์
            assert content == test_content
            assert isinstance(content, str)
            assert len(content) > 0

        finally:
            # ลบไฟล์ชั่วคราว
            Path(temp_path).unlink()

    def test_load_prompt_file_not_found(self):
        """ทดสอบเมื่อไฟล์ไม่พบ"""
        non_existent_file = "non_existent_prompt.txt"

        with pytest.raises(PromptLoadError) as exc_info:
            load_prompt(non_existent_file)

        assert "ไม่พบไฟล์ prompt" in str(exc_info.value)

    def test_load_prompt_empty_file(self):
        """ทดสอบเมื่อไฟล์ว่าง"""
        # สร้างไฟล์ว่าง
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write("")  # ไฟล์ว่าง
            temp_path = f.name

        try:
            with pytest.raises(PromptLoadError) as exc_info:
                load_prompt(temp_path)

            assert "ไฟล์ prompt ว่าง" in str(exc_info.value)

        finally:
            Path(temp_path).unlink()

    def test_load_prompt_whitespace_only(self):
        """ทดสอบเมื่อไฟล์มีแต่ช่องว่าง"""
        # สร้างไฟล์ที่มีแต่ช่องว่าง
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write("   \n   \t   \n   ")  # มีแต่ whitespace
            temp_path = f.name

        try:
            with pytest.raises(PromptLoadError) as exc_info:
                load_prompt(temp_path)

            assert "ไฟล์ prompt ว่าง" in str(exc_info.value)

        finally:
            Path(temp_path).unlink()

    def test_load_prompt_directory_instead_of_file(self):
        """ทดสอบเมื่อส่ง directory แทนไฟล์"""
        with tempfile.TemporaryDirectory() as temp_dir:
            with pytest.raises(PromptLoadError) as exc_info:
                load_prompt(temp_dir)

            assert "ไม่ใช่ไฟล์" in str(exc_info.value)

    def test_load_prompt_with_path_object(self):
        """ทดสอบการใช้ Path object"""
        # สร้างไฟล์ชั่วคราว
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            test_content = "ทดสอบการใช้ Path object"
            f.write(test_content)
            temp_path = Path(f.name)

        try:
            # โหลด prompt ด้วย Path object
            content = load_prompt(temp_path)

            assert content == test_content

        finally:
            temp_path.unlink()

    def test_load_prompt_thai_content(self):
        """ทดสอบการโหลดเนื้อหาภาษาไทย"""
        thai_content = """คุณคือ AI ผู้ช่วยสำหรับช่อง YouTube ธรรมะดีดี
        
กรุณาช่วยวิเคราะห์เทรนด์และสร้างหัวข้อคอนเทนต์ที่เข้ากับแบรนด์

เป้าหมาย:
- สร้างความสุขให้ผู้ชม
- เนื้อหาเชิงบวกและสร้างสรรค์
- นำหลักธรรมมาประยุกต์ในชีวิตประจำวัน"""

        # สร้างไฟล์ชั่วคราว
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(thai_content)
            temp_path = f.name

        try:
            # โหลด prompt
            content = load_prompt(temp_path)

            # ตรวจสอบว่าภาษาไทยโหลดได้ถูกต้อง
            assert "ธรรมะดีดี" in content
            assert "วิเคราะห์เทรนด์" in content
            assert "หลักธรรม" in content
            assert content == thai_content

        finally:
            Path(temp_path).unlink()

    def test_load_prompt_custom_encoding(self):
        """ทดสอบการใช้ encoding ที่กำหนดเอง"""
        # สร้างไฟล์ด้วย encoding ที่แตกต่าง
        test_content = "ทดสอบ encoding ภาษาไทย"

        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(test_content)
            temp_path = f.name

        try:
            # โหลดด้วย encoding ที่ถูกต้อง
            content = load_prompt(temp_path, encoding='utf-8')
            assert content == test_content

        finally:
            Path(temp_path).unlink()


class TestGetPromptPath:
    """ทดสอบฟังก์ชัน get_prompt_path"""

    def test_get_prompt_path_basic(self):
        """ทดสอบการสร้าง path พื้นฐาน"""
        prompt_name = "trend_scout_v1.txt"
        path = get_prompt_path(prompt_name)

        assert isinstance(path, Path)
        assert prompt_name in str(path)
        assert "prompts" in str(path)

    def test_get_prompt_path_custom_dir(self):
        """ทดสอบการใช้ prompts directory ที่กำหนดเอง"""
        prompt_name = "test_prompt.txt"
        custom_dir = "custom_prompts"

        path = get_prompt_path(prompt_name, custom_dir)

        assert isinstance(path, Path)
        assert prompt_name in str(path)
        assert custom_dir in str(path)


class TestPromptIntegration:
    """ทดสอบการรวมกับไฟล์ prompt จริง"""

    def test_load_trend_scout_prompt(self):
        """ทดสอบการโหลด prompt ของ TrendScoutAgent"""
        # หา path ของ prompt file
        prompt_path = Path("prompts/trend_scout_v1.txt")

        if prompt_path.exists():
            # โหลด prompt
            content = load_prompt(prompt_path)

            # ตรวจสอบเนื้อหา
            assert len(content) > 0
            assert isinstance(content, str)

            # ตรวจสอบคำสำคัญที่ควรมี
            assert "TrendScoutAgent" in content or "วิเคราะห์เทรนด์" in content
            assert "JSON" in content  # ควรมีรูปแบบ output

            # ตรวจสอบว่าไม่มี encoding error
            assert "ธรรมะ" in content or "YouTube" in content
        else:
            pytest.skip("ไม่พบไฟล์ trend_scout_v1.txt")

    def test_prompt_not_empty_after_loading(self):
        """ทดสอบว่า prompt ที่โหลดมาไม่ว่าง"""
        prompt_path = Path("prompts/trend_scout_v1.txt")

        if prompt_path.exists():
            content = load_prompt(prompt_path)

            # ตรวจสอบว่าไม่ว่าง
            assert content.strip() != ""
            assert len(content.strip()) > 100  # ควรมีเนื้อหาพอสมควร
        else:
            pytest.skip("ไม่พบไฟล์ trend_scout_v1.txt")
