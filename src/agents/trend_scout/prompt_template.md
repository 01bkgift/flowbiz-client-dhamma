# Prompt Template Mapping สำหรับ TrendScoutAgent

## วัตถุประสงค์
เอกสารนี้อธิบายการ mapping ระหว่าง prompt template และ model schema สำหรับ TrendScoutAgent

## Schema Mapping

### Input Schema (TrendScoutInput)
```python
{
  "keywords": List[str],                    # คำสำคัญที่ต้องการวิเคราะห์
  "google_trends": List[GoogleTrendItem],   # ข้อมูลเทรนด์จาก Google
  "youtube_trending_raw": List[YTTrendingItem], # วิดีโอเทรนด์ใน YouTube
  "competitor_comments": List[CompetitorComment], # ความคิดเห็นจากคู่แข่ง
  "embeddings_similar_groups": List[EmbeddingSimilarGroup] # กลุ่มคำที่คล้ายกัน
}
```

### Output Schema (TrendScoutOutput)
```python
{
  "generated_at": datetime,
  "topics": List[TopicEntry],      # หัวข้อที่แนะนำ (สูงสุด 15)
  "discarded_duplicates": List[str],
  "meta": MetaInfo
}
```

### TopicEntry Structure
```python
{
  "rank": int,                     # อันดับ
  "title": str,                    # ชื่อหัวข้อ (≤ 60 ตัวอักษร)
  "pillar": str,                   # เสาหลักเนื้อหา
  "predicted_14d_views": int,      # การดูคาดการณ์ 14 วัน
  "scores": {
    "search_intent": float,        # ความตั้งใจค้นหา [0-1]
    "freshness": float,            # ความใหม่ [0-1]
    "evergreen": float,            # ความคงทน [0-1]
    "brand_fit": float,            # ความเข้ากับแบรนด์ [0-1]
    "composite": float             # คะแนนรวม [0-1]
  },
  "reason": str,                   # เหตุผลที่แนะนำ
  "raw_keywords": List[str],       # คำสำคัญต้นฉบับ
  "similar_to": List[str],         # คล้ายกับหัวข้ออื่น
  "risk_flags": List[str]          # ธงเตือนความเสี่ยง
}
```

## การใช้งาน Prompt Template

1. **โหลด Prompt**: ใช้ `load_prompt("prompts/trend_scout_v1.txt")`
2. **แทนที่ Variables**: แทนที่ `{keywords}`, `{google_trends}` ฯลฯ ในข้อความ prompt
3. **ส่งไปยัง LLM**: ส่ง prompt ที่สมบูรณ์ไปยัง LLM
4. **Parse Response**: แปลง JSON response เป็น TrendScoutOutput

## Content Pillars
เสาหลักเนื้อหาของช่อง "ธรรมะดีดี":
- ธรรมะประยุกต์
- การทำสมาธิ  
- จิตใจและความสุข
- วิธีรับมือความเครียด
- การปล่อยวาง
- พุทธธรรมในชีวิตประจำวัน

## คะแนนน้ำหนัก (Score Weights)
- search_intent: 30%
- freshness: 25%
- evergreen: 25% 
- brand_fit: 20%

## ข้อกำหนดเพิ่มเติม
- ชื่อหัวข้อยาวไม่เกิน 60 ตัวอักษร (แนะนำ ≤ 34 สำหรับ YouTube)
- คะแนนทั้งหมดต้องอยู่ในช่วง 0.0 - 1.0
- หัวข้อต้องเรียงลำดับตามคะแนน composite จากมากไปน้อย
- จำนวนหัวข้อสูงสุด 15 หัวข้อ