# 📝 Prompt Templates Overview

คู่มือสำหรับการจัดการ Prompt Templates ในระบบ Dhamma Automation

## 🎯 หลักการจัดการ Prompt

### ทำไมต้องแยก Prompt ออกจากโค้ด?

1. **Maintainability**: แก้ไข prompt ได้โดยไม่ต้องแก้โค้ด
2. **Version Control**: ติดตาม changes และ rollback ได้
3. **A/B Testing**: ทดสอบ prompt หลายเวอร์ชันได้ง่าย
4. **Collaboration**: Non-technical team สามารถแก้ prompt ได้
5. **Security**: ไม่มี sensitive content ใน source code

### การตั้งชื่อไฟล์

```
prompts/
├── {agent_name}_v{version}.txt
├── trend_scout_v1.txt          # เวอร์ชัน 1
├── trend_scout_v2.txt          # เวอร์ชัน 2 (ปรับปรุง)
├── topic_prioritizer_v1.txt
├── outline_agent_v1.txt
└── script_writer_v1.txt
```

**รูปแบบ**: `{agent_name}_v{version}.txt`
- **agent_name**: ชื่อ Agent (snake_case)
- **version**: เลขเวอร์ชัน (1, 2, 3, ...)
- **extension**: .txt สำหรับ readability

## 📋 Prompt Templates ปัจจุบัน

### 1. TrendScoutAgent (trend_scout_v1.txt)

**วัตถุประสงค์**: วิเคราะห์เทรนด์และสร้างหัวข้อคอนเทนต์

**Input Variables**:
```
{keywords}                  # รายการคำสำคัญ
{google_trends}            # ข้อมูล Google Trends  
{youtube_trending_raw}     # วิดีโอเทรนด์ YouTube
{competitor_comments}      # ความคิดเห็นคู่แข่ง
{embeddings_similar_groups} # กลุ่มคำคล้าย
```

**Output Format**: JSON ตาม TrendScoutOutput schema

**เสาหลักเนื้อหา**:
- ธรรมะประยุกต์
- การทำสมาธิ
- จิตใจและความสุข
- วิธีรับมือความเครียด
- การปล่อยวาง
- พุทธธรรมในชีวิตประจำวัน

**การให้คะแนน**:
- search_intent (30%): ความตั้งใจค้นหา
- freshness (25%): ความใหม่
- evergreen (25%): ความคงทน
- brand_fit (20%): ความเข้ากับแบรนด์

**ตัวอย่างการใช้งาน**:
```python
from automation_core.prompt_loader import load_prompt, get_prompt_path

# โหลด prompt
prompt_path = get_prompt_path("trend_scout_v1.txt")
prompt_template = load_prompt(prompt_path)

# แทนที่ตัวแปร
filled_prompt = prompt_template.format(
    keywords=input_data.keywords,
    google_trends=input_data.google_trends,
    # ...
)
```

### 2. ResearchRetrievalAgent (research_retrieval_v1.txt)

**วัตถุประสงค์**: ค้นหาและดึงข้อความอ้างอิงจากคลังธรรมะสำหรับสร้างคอนเทนต์

**Input Variables**:
```
{topic_title}           # หัวข้อหลักที่ต้องการค้นหา
{raw_query}            # คำค้นหาเริ่มต้น
{refinement_hints}     # คำแนะนำในการปรับแต่งคำค้น
{max_passages}         # จำนวน passages สูงสุด
{required_tags}        # แท็กที่จำเป็นต้องมี
{forbidden_sources}    # แหล่งที่ห้ามใช้
```

**Output Format**: JSON ตาม ResearchRetrievalOutput schema

**ประเภท Passages**:
- **Primary**: passages หลักที่เกี่ยวข้องโดยตรง
- **Supportive**: passages สนับสนุนเพิ่มเติม

**การประเมิน Relevance**:
- semantic_sim (55%): ความคล้ายความหมาย
- keyword_boost (20%): การตรงกับคำสำคัญ
- tag_match (15%): การตรงกับแท็กที่ต้องการ
- recency_decay (10%): ความใหม่ของข้อมูล

**คุณสมบัติพิเศษ**:
- การสร้าง summary bullets อัตโนมัติ
- การประเมิน coverage assessment
- การตรวจสอบลิขสิทธิ์
- การจัดการ missing concepts

## 🔄 Prompt Templates ในอนาคต

### 2. TopicPrioritizerAgent (topic_prioritizer_v1.txt) - Phase 1

**วัตถุประสงค์**: จัดลำดับความสำคัญของหัวข้อตามเกณฑ์ธุรกิจ

**Input Variables**:
```
{topics}               # หัวข้อจาก TrendScout
{business_goals}       # เป้าหมายธุรกิจ
{audience_segments}    # กลุ่มเป้าหมาย
{resource_constraints} # ข้อจำกัดทรัพยากร
```

**การประเมิน**:
- ROI คาดการณ์ (40%)
- ความเสี่ยง (25%)
- ความเข้ากับแบรนด์ (20%)
- ความยากในการผลิต (15%)

### 3. RetrievalAgent (retrieval_v1.txt) - Phase 1

**วัตถุประสงค์**: ค้นหาและรวบรวมข้อมูลสำหรับการสร้างเนื้อหา

**Input Variables**:
```
{topic}                # หัวข้อที่เลือก
{search_queries}       # คำค้นหา
{source_types}         # ประเภทแหล่งข้อมูล
{quality_criteria}     # เกณฑ์คุณภาพ
```

### 4. OutlineAgent (outline_v1.txt) - Phase 2

**วัตถุประสงค์**: สร้างโครงเรื่องสำหรับวิดีโอ

**Input Variables**:
```
{topic}                # หัวข้อ
{target_duration}      # ความยาววิดีโอ
{audience_level}       # ระดับผู้ชม
{key_points}          # จุดสำคัญ
{supporting_data}     # ข้อมูลสนับสนุน
```

### 5. ScriptWriterAgent (script_writer_v1.txt) - Phase 2

**วัตถุประสงค์**: เขียนสคริปต์วิดีโอ

**Input Variables**:
```
{outline}             # โครงเรื่อง
{tone}               # น้ำเสียง
{call_to_action}     # การเรียกร้องปฏิบัติ
{brand_guidelines}   # แนวทางแบรนด์
```

### 6. ValidatorAgent (validator_v1.txt) - Phase 3

**วัตถุประสงค์**: ตรวจสอบคุณภาพเนื้อหา

**Input Variables**:
```
{content}            # เนื้อหาที่ต้องตรวจ
{quality_checklist}  # รายการตรวจสอบ
{brand_compliance}   # การปฏิบัติตามแบรนด์
{target_metrics}     # เป้าหมายตัวชี้วัด
```

## 🛠️ Prompt Engineering Best Practices

### 1. โครงสร้าง Prompt ที่ดี

```
# Role Definition
คุณคือ AI Agent สำหรับ...

## บทบาทและหน้าที่
- หน้าที่หลัก 1
- หน้าที่หลัก 2

## ข้อมูลที่ได้รับ
**ตัวแปร 1:** {variable1}
**ตัวแปร 2:** {variable2}

## เกณฑ์/หลักการ
1. หลักการ 1
2. หลักการ 2

## ข้อจำกัด
- ข้อจำกัด 1
- ข้อจำกัด 2

## รูปแบบ Output
{
  "field1": "value",
  "field2": [...]
}

## คำแนะนำเพิ่มเติม
- แนะนำ 1
- แนะนำ 2

กรุณาประมวลผลตามที่ระบุ
```

### 2. การใช้ Variables

**Good**:
```
**คำสำคัญ:** {keywords}
**ข้อมูลเทรนด์:** {google_trends}
```

**Avoid**:
```
คำสำคัญคือ {keywords} และเทรนด์คือ {google_trends}
```

### 3. การกำหนด Output Format

**ใช้ JSON Schema**:
```json
{
  "generated_at": "ISO datetime",
  "results": [
    {
      "field1": "string",
      "field2": "number",
      "field3": ["array"]
    }
  ],
  "metadata": {
    "field4": "value"
  }
}
```

## 🔧 การใช้งาน Prompt Loader

### โหลด Prompt Template

```python
from automation_core.prompt_loader import load_prompt, get_prompt_path

# วิธีที่ 1: ระบุ path โดยตรง
prompt = load_prompt("prompts/trend_scout_v1.txt")

# วิธีที่ 2: ใช้ helper function
prompt_path = get_prompt_path("trend_scout_v1.txt")
prompt = load_prompt(prompt_path)
```

### แทนที่ Variables

```python
# วิธีที่ 1: str.format()
filled_prompt = prompt.format(
    keywords=input_data.keywords,
    google_trends=json.dumps(input_data.google_trends, ensure_ascii=False)
)

# วิธีที่ 2: Template engine (อนาคต)
from jinja2 import Template
template = Template(prompt)
filled_prompt = template.render(
    keywords=input_data.keywords,
    google_trends=input_data.google_trends
)
```

### Error Handling

```python
from automation_core.prompt_loader import PromptLoadError

try:
    prompt = load_prompt("prompts/agent_v1.txt")
except PromptLoadError as e:
    logger.error(f"ไม่สามารถโหลด prompt: {e}")
    # Fallback หรือ default prompt
```

## 📊 Prompt Versioning Strategy

### การอัปเกรด Prompt

```
prompts/
├── trend_scout_v1.txt          # เวอร์ชันเดิม (stable)
├── trend_scout_v2.txt          # เวอร์ชันใหม่ (testing)
└── trend_scout_v3.txt          # เวอร์ชันล่าสุด (experimental)
```

### การ A/B Testing

```python
class TrendScoutAgent:
    def __init__(self, prompt_version: str = "v1"):
        self.prompt_version = prompt_version
    
    def _load_prompt(self) -> str:
        prompt_file = f"trend_scout_{self.prompt_version}.txt"
        return load_prompt(get_prompt_path(prompt_file))
```

### การ Rollback

```bash
# Git tag สำหรับ prompt versions
git tag prompt-trend-scout-v1
git tag prompt-trend-scout-v2

# Rollback เมื่อมีปัญหา
git checkout prompt-trend-scout-v1 -- prompts/trend_scout_v2.txt
```

## 🧪 การทดสอบ Prompt

### Unit Tests สำหรับ Prompt Loading

```python
def test_load_trend_scout_prompt():
    """ทดสอบการโหลด prompt ของ TrendScout"""
    prompt = load_prompt(get_prompt_path("trend_scout_v1.txt"))
    
    # ตรวจสอบเนื้อหา
    assert "TrendScoutAgent" in prompt or "วิเคราะห์เทรนด์" in prompt
    assert "{keywords}" in prompt
    assert "{google_trends}" in prompt
    assert "JSON" in prompt
```

### Integration Tests

```python
def test_prompt_template_filling():
    """ทดสอบการแทนที่ตัวแปรใน prompt"""
    prompt = load_prompt(get_prompt_path("trend_scout_v1.txt"))
    
    test_data = {
        "keywords": ["ปล่อยวาง", "นอนไม่หลับ"],
        "google_trends": [{"term": "test", "score": 50}]
    }
    
    filled = prompt.format(**test_data)
    
    # ตรวจสอบว่าไม่มี {variables} เหลือ
    assert "{keywords}" not in filled
    assert "{google_trends}" not in filled
    assert "ปล่อยวาง" in filled
```

## 📈 การวัดประสิทธิภาพ Prompt

### Metrics ที่ควรติดตาม

1. **Accuracy**: ความถูกต้องของ output
2. **Consistency**: ความสม่ำเสมอของผลลัพธ์
3. **Relevance**: ความเกี่ยวข้องกับ input
4. **Quality**: คุณภาพของเนื้อหาที่สร้าง

### A/B Testing Framework

```python
class PromptTester:
    def __init__(self):
        self.results = {}
    
    def test_prompt_versions(self, test_data: List[dict]) -> dict:
        """ทดสอบ prompt หลายเวอร์ชันกับข้อมูลเดียวกัน"""
        
        for version in ["v1", "v2", "v3"]:
            agent = TrendScoutAgent(prompt_version=version)
            results = []
            
            for data in test_data:
                result = agent.run(data)
                results.append(self._evaluate_result(result))
            
            self.results[version] = {
                "avg_score": sum(results) / len(results),
                "consistency": self._calculate_consistency(results)
            }
        
        return self.results
```

## 🔒 Security Considerations

### Prompt Injection Prevention

1. **Input Sanitization**: ทำความสะอาด user input
2. **Template Validation**: ตรวจสอบ template syntax
3. **Output Filtering**: กรองเนื้อหาที่ไม่เหมาะสม

### Sensitive Data Handling

```python
def sanitize_input(data: dict) -> dict:
    """ลบข้อมูลสำคัญออกจาก input"""
    
    sensitive_fields = ["api_key", "password", "token"]
    cleaned = data.copy()
    
    for field in sensitive_fields:
        if field in cleaned:
            cleaned[field] = "[REDACTED]"
    
    return cleaned
```

---

📚 **อ่านต่อ**: [Agent Lifecycle](AGENT_LIFECYCLE.md) | [Troubleshooting](TROUBLESHOOTING.md)