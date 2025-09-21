# 🔧 แก้ไขปัญหา (Troubleshooting)

คู่มือแก้ไขปัญหาที่พบบ่อยในระบบ Dhamma Automation

## 🚨 ปัญหาที่พบบ่อย

### 1. 📦 ปัญหาการติดตั้ง (Installation Issues)

#### Import Error: ไม่พบโมดูล

**อาการ**:
```bash
ModuleNotFoundError: No module named 'automation_core'
ModuleNotFoundError: No module named 'agents'
```

**สาเหตุ**:
- ติดตั้ง package ไม่สำเร็จ
- Python path ไม่ถูกต้อง
- Virtual environment ไม่ได้เปิดใช้งาน

**วิธีแก้ไข**:
```bash
# 1. ตรวจสอบ Python path
python -c "import sys; print(sys.path)"

# 2. ติดตั้งแบบ editable mode
pip install -e .

# 3. หรือเพิ่ม PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# 4. ตรวจสอบ virtual environment
which python
pip list | grep dhamma
```

#### Dependency Conflicts

**อาการ**:
```bash
ERROR: pip's dependency resolver does not currently consider all the dependencies
```

**วิธีแก้ไข**:
```bash
# 1. สร้าง virtual environment ใหม่
python -m venv venv_clean
source venv_clean/bin/activate  # หรือ venv_clean\Scripts\activate บน Windows

# 2. อัปเกรด pip
pip install --upgrade pip

# 3. ติดตั้งทีละตัว
pip install pydantic
pip install typer[all]
pip install rich
pip install -e .
```

### 2. 🔍 ปัญหา CLI (Command Line Issues)

#### คำสั่ง `dhamma-automation` ไม่พบ

**อาการ**:
```bash
dhamma-automation: command not found
```

**วิธีแก้ไข**:
```bash
# วิธีที่ 1: ใช้ python -m
python -m cli.main trend-scout --help

# วิธีที่ 2: ติดตั้งใหม่
pip install -e .

# วิธีที่ 3: ตรวจสอบ PATH
echo $PATH
pip show dhamma-automation
```

#### ไฟล์ Input ไม่พบ

**อาการ**:
```bash
Error: Invalid value for '--input' / '-i': File 'data.json' does not exist.
```

**วิธีแก้ไข**:
```bash
# 1. ตรวจสอบ path
ls -la src/agents/trend_scout/mock_input.json

# 2. ใช้ absolute path
python -m cli.main trend-scout \
  --input "$(pwd)/src/agents/trend_scout/mock_input.json" \
  --out output/result.json

# 3. สร้างไฟล์ input ตัวอย่าง
cp src/agents/trend_scout/mock_input.json ./input.json
```

### 3. 📝 ปัญหา Prompt Loading

#### ไฟล์ Prompt ไม่พบ

**อาการ**:
```python
PromptLoadError: ไม่พบไฟล์ prompt: prompts/trend_scout_v1.txt
```

**การตรวจสอบ**:
```bash
# ตรวจสอบว่าไฟล์มีอยู่จริง
ls -la prompts/
find . -name "trend_scout_v1.txt"
```

**วิธีแก้ไข**:
```python
# ใช้ absolute path
from pathlib import Path
prompt_path = Path(__file__).parent.parent / "prompts" / "trend_scout_v1.txt"

# หรือตรวจสอบใน code
import os
if not os.path.exists("prompts/trend_scout_v1.txt"):
    print("Prompt file not found!")
    print("Current directory:", os.getcwd())
    print("Files in prompts/:", os.listdir("prompts/"))
```

#### Encoding Error

**อาการ**:
```python
UnicodeDecodeError: 'utf-8' codec can't decode byte
```

**วิธีแก้ไข**:
```python
# ลองเปลี่ยน encoding
prompt = load_prompt("prompts/trend_scout_v1.txt", encoding="utf-8-sig")

# หรือตรวจสอบ encoding ของไฟล์
file prompts/trend_scout_v1.txt
```

### 4. 🧪 ปัญหา Testing

#### Tests ไม่ผ่าน

**อาการ**:
```bash
FAILED tests/test_trend_scout_agent.py::test_run_basic_functionality
```

**การตรวจสอบ**:
```bash
# รัน test แบบ verbose
pytest -v tests/test_trend_scout_agent.py

# รัน test เฉพาะตัวที่ fail
pytest tests/test_trend_scout_agent.py::test_run_basic_functionality -v

# ดู coverage
pytest --cov=src --cov=cli tests/
```

**สาเหตุและแก้ไข**:
```python
# 1. Mock data ไม่ถูกต้อง - ตรวจสอบ schema
def test_with_valid_input():
    input_data = TrendScoutInput(
        keywords=["test"],  # ต้องมี keywords
        google_trends=[],   # สามารถเป็น empty list ได้
        # ... ฟิลด์อื่นๆ
    )

# 2. Deterministic testing - ใช้ seed
import random
random.seed(42)  # ใน test setup

# 3. File path issues - ใช้ relative path
test_file = Path(__file__).parent / "fixtures" / "test_input.json"
```

#### Import Errors ใน Tests

**อาการ**:
```bash
ModuleNotFoundError: No module named 'automation_core'
```

**วิธีแก้ไข**:
```bash
# 1. รัน tests จาก root directory
cd /path/to/dhamma-channel-automation
pytest

# 2. ตั้งค่า PYTHONPATH
export PYTHONPATH="$(pwd):$PYTHONPATH"
pytest

# 3. ใช้ -e flag เมื่อติดตั้ง
pip install -e .
```

### 5. 🌐 ปัญหา MkDocs

#### MkDocs Build ล้มเหลว

**อาการ**:
```bash
mkdocs build
ERROR - Config value: 'theme.language': Expected one of: en, ...
```

**วิธีแก้ไข**:
```yaml
# แก้ไข mkdocs.yml
theme:
  name: material
  language: th  # เปลี่ยนเป็น en ถ้า th ไม่รองรับ
```

#### Plugin ไม่พบ

**อาการ**:
```bash
Config value: 'plugins': No such config option: git-revision-date-localized
```

**วิธีแก้ไข**:
```bash
# ติดตั้ง plugins ที่ขาด
pip install mkdocs-git-revision-date-localized-plugin
pip install mkdocs-minify-plugin

# หรือลบออกจาก mkdocs.yml ชั่วคราว
# plugins:
#   - git-revision-date-localized  # comment out
```

### 6. 📊 ปัญหาประสิทธิภาพ (Performance Issues)

#### Agent ทำงานช้า

**การวินิจฉัย**:
```python
import time
import logging

logging.basicConfig(level=logging.DEBUG)

start_time = time.time()
result = agent.run(input_data)
end_time = time.time()

print(f"Agent took {end_time - start_time:.2f} seconds")
```

**การปรับปรุง**:
```python
# 1. Caching
from functools import lru_cache

@lru_cache(maxsize=100)
def expensive_operation(key):
    # ปฏิบัติการที่ใช้เวลานาน
    pass

# 2. Lazy loading
class TrendScoutAgent:
    def __init__(self):
        self._prompt = None
    
    @property
    def prompt(self):
        if self._prompt is None:
            self._prompt = load_prompt("prompts/trend_scout_v1.txt")
        return self._prompt

# 3. Batch processing
def process_multiple_inputs(inputs):
    # ประมวลผลหลาย inputs พร้อมกัน
    pass
```

#### Memory Usage สูง

**การตรวจสอบ**:
```python
import psutil
import os

process = psutil.Process(os.getpid())
memory_mb = process.memory_info().rss / 1024 / 1024
print(f"Memory usage: {memory_mb:.2f} MB")
```

**วิธีลด Memory**:
```python
# 1. ลบ objects ที่ไม่ใช้
del large_object
import gc
gc.collect()

# 2. ใช้ generators แทน lists
def generate_topics():
    for topic in process_topics():
        yield topic

# 3. จำกัด batch size
BATCH_SIZE = 10
for batch in chunks(large_list, BATCH_SIZE):
    process_batch(batch)
```

### 7. 🔐 ปัญหา Security & Configuration

#### Environment Variables ไม่ทำงาน

**อาการ**:
```python
config.openai_api_key is None
```

**การตรวจสอบ**:
```bash
# ตรวจสอบว่ามีไฟล์ .env
ls -la .env

# ตรวจสอบเนื้อหา
cat .env

# ตรวจสอบใน Python
from automation_core.config import config
print(config.dict())
```

**วิธีแก้ไข**:
```bash
# 1. สร้างไฟล์ .env
cp .env.example .env

# 2. ตั้งค่า environment variables
export OPENAI_API_KEY="your-key-here"

# 3. ตรวจสอบการโหลด
python -c "from automation_core.config import config; print(config.openai_api_key)"
```

## 🛠️ การ Debug เชิงลึก

### เปิดใช้งาน Debug Mode

```python
# ใน automation_core/logging.py
logger = setup_logging(log_level="DEBUG")

# หรือใน environment
export LOG_LEVEL="DEBUG"
```

### การ Profile ประสิทธิภาพ

```python
import cProfile
import pstats

# Profile Agent
pr = cProfile.Profile()
pr.enable()

result = agent.run(input_data)

pr.disable()
stats = pstats.Stats(pr)
stats.sort_stats('cumulative')
stats.print_stats(10)  # แสดง top 10 functions
```

### การทำ Memory Profiling

```bash
# ติดตั้ง memory_profiler
pip install memory-profiler

# ใช้ decorator
@profile
def run_agent():
    agent = TrendScoutAgent()
    return agent.run(input_data)

# รันและดูผล
python -m memory_profiler script.py
```

## 📞 ขอความช่วยเหลือ

### ก่อนขอความช่วยเหลือ

1. **ตรวจสอบ logs**:
   ```bash
   tail -f logs/app.log
   ```

2. **รวบรวมข้อมูล**:
   ```bash
   python --version
   pip list
   python -c "import automation_core; print(automation_core.__file__)"
   ```

3. **ทำซ้ำปัญหา**:
   - ขั้นตอนที่ทำให้เกิดปัญหา
   - Input data ที่ใช้
   - Error messages ที่เกิดขึ้น

### การรายงานปัญหา

**เทมเพลต Issue**:
```markdown
## ปัญหาที่พบ
[อธิบายปัญหาอย่างชัดเจน]

## ขั้นตอนการทำซ้ำ
1. รันคำสั่ง...
2. ใส่ input...
3. เกิดข้อผิดพลาด...

## ผลลัพธ์ที่คาดหวัง
[สิ่งที่ควรเกิดขึ้น]

## ผลลัพธ์จริง
[สิ่งที่เกิดขึ้นจริง]

## สภาพแวดล้อม
- OS: [Windows/Mac/Linux]
- Python version: [3.11+]
- Package version: [ระบุเวอร์ชัน]

## Logs/Error messages
```
[วาง error messages ที่นี่]
```

## Additional context
[ข้อมูลเพิ่มเติมที่อาจเกี่ยวข้อง]
```

### ช่องทางการติดต่อ

- 🐛 **Bug Reports**: [GitHub Issues](https://github.com/natbkgift/dhamma-channel-automation/issues)
- 💡 **Feature Requests**: [GitHub Discussions](https://github.com/natbkgift/dhamma-channel-automation/discussions)
- 📖 **Documentation**: อ่านเอกสารนี้และ [Architecture](ARCHITECTURE.md)

## 🔍 Quick Fix Commands

### Reset Environment
```bash
# ลบ virtual environment และสร้างใหม่
rm -rf venv
python -m venv venv
source venv/bin/activate
pip install -e .
```

### Clean Installation
```bash
# ทำความสะอาดและติดตั้งใหม่
pip uninstall dhamma-automation
pip cache purge
pip install -e .
```

### Verify Installation
```bash
# ตรวจสอบการติดตั้ง
python -c "from automation_core import BaseAgent; print('✅ Core OK')"
python -c "from agents.trend_scout import TrendScoutAgent; print('✅ Agents OK')"
python -c "from cli.main import app; print('✅ CLI OK')"
```

### Test Everything
```bash
# รัน test suite ทั้งหมด
pytest -v
python -m cli.main trend-scout --input src/agents/trend_scout/mock_input.json --out /tmp/test.json
mkdocs build
```

---

💡 **เคล็ดลับ**: เก็บ command history และ error logs ไว้ - จะช่วยในการแก้ไขปัญหาได้เร็วขึ้น