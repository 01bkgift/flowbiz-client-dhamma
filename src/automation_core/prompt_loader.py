"""
ระบบโหลด Prompt Templates จากไฟล์ภายนอก
ป้องกันการฝัง prompt ยาวๆ ในโค้ด
"""

from pathlib import Path


class PromptLoadError(Exception):
    """Exception สำหรับปัญหาการโหลด prompt"""
    pass


def load_prompt(path: str | Path, encoding: str = "utf-8") -> str:
    """
    โหลด prompt template จากไฟล์
    
    Args:
        path: path ไปยังไฟล์ prompt
        encoding: encoding ของไฟล์ (default: utf-8)
        
    Returns:
        เนื้อหา prompt เป็น string
        
    Raises:
        PromptLoadError: เมื่อไฟล์ไม่พบ หรือมีปัญหาในการอ่าน
    """

    # แปลง path เป็น Path object
    prompt_path = Path(path)

    # ตรวจสอบว่าไฟล์มีอยู่จริง
    if not prompt_path.exists():
        raise PromptLoadError(f"ไม่พบไฟล์ prompt: {prompt_path}")

    # ตรวจสอบว่าเป็นไฟล์ (ไม่ใช่โฟลเดอร์)
    if not prompt_path.is_file():
        raise PromptLoadError(f"Path ไม่ใช่ไฟล์: {prompt_path}")

    try:
        # อ่านไฟล์
        with open(prompt_path, encoding=encoding) as f:
            content = f.read().strip()

        # ตรวจสอบว่าไฟล์ไม่ว่าง
        if not content:
            raise PromptLoadError(f"ไฟล์ prompt ว่าง: {prompt_path}")

        return content

    except UnicodeDecodeError as e:
        raise PromptLoadError(f"ปัญหา encoding ในไฟล์ {prompt_path}: {e}")
    except OSError as e:
        raise PromptLoadError(f"ไม่สามารถอ่านไฟล์ {prompt_path}: {e}")


def get_prompt_path(prompt_name: str, prompts_dir: str = "prompts") -> Path:
    """
    สร้าง path สำหรับไฟล์ prompt
    
    Args:
        prompt_name: ชื่อไฟล์ prompt (เช่น "trend_scout_v1.txt")
        prompts_dir: โฟลเดอร์ที่เก็บ prompts
        
    Returns:
        Path object ไปยังไฟล์ prompt
    """

    # หา root directory ของโครงการ
    current_dir = Path(__file__).parent
    while current_dir.parent != current_dir:
        if (current_dir / prompts_dir).exists():
            return current_dir / prompts_dir / prompt_name
        current_dir = current_dir.parent

    # ถ้าไม่พบ ให้ใช้ relative path
    return Path(prompts_dir) / prompt_name
