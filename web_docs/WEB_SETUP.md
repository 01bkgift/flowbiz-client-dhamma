# วิธีติดตั้งและรัน Web UI (ภาษาไทย)

## รันบนเครื่อง
```bash
python -m venv .venv
# Windows
.\.venv\Scripts\activate
# Linux/Mac
# source .venv/bin/activate

pip install -r requirements.web.txt
uvicorn app.main:app --reload
```

## เข้าระบบ
- URL: http://localhost:8000
- บัญชีเริ่มต้น:
  - Username: admin
  - Password: admin123
(แก้ไขได้ในไฟล์ .env — แนะนำเปลี่ยนทันที)

## Pipeline ที่เว็บเรียก
- pipeline.web.yml: Trend → Outline → Script → Validate → Subtitle → SEO → Publish

## ความปลอดภัยขั้นพื้นฐาน
- เปลี่ยน SECRET_KEY และ admin/password ใน .env
- ใช้ reverse proxy + HTTPS หากใช้งานร่วมกันหลายคน
- บน Windows ตั้ง PYTHON_BIN ใน .env ให้ชี้ไปยัง .venv\Scripts\python.exe

## รันด้วย Docker
```bash
docker compose up --build
```
เปิด http://localhost:8000

## Logs/Persistence
- Logs รายเอเจนต์: output/logs/<agent>.log
- ผลลัพธ์ Pipeline: output/pipelines/<run_id>/
