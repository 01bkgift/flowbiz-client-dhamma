# Runbook: Soft-Live (Unlisted) Verification on VPS

> **วัตถุประสงค์**: ทดสอบ upload YouTube แบบ unlisted บน production VPS เพื่อยืนยันว่า pipeline ทำงานได้จริง

---

## ⚠️ Safety Guardrails

> [!CAUTION]
> **กฎความปลอดภัยที่ต้องปฏิบัติตาม:**

| กฎ | รายละเอียด |
|----|------------|
| ใช้เฉพาะ `SOFT_LIVE_YOUTUBE_MODE=unlisted` | ห้ามใช้ `public` ในการทดสอบ |
| ตรวจสอบ port binding | ต้องเป็น `127.0.0.1` เท่านั้น ห้าม `0.0.0.0` |
| ใช้ test video สั้นๆ | ไฟล์ทดสอบต้องสั้นและไม่มีเนื้อหาอ่อนไหว |
| ตั้งชื่อ video ที่ระบุตัวตนได้ | เพื่อง่ายต่อการลบภายหลัง |
| เปิด `SOFT_LIVE_FAIL_CLOSED=true` | Fail-safe หาก config ผิดพลาด |

---

## A) Pre-Checks (หยุดทันทีหากไม่ผ่าน)

### 1. ตรวจสอบ Service Health

```bash
curl -fsS https://dhamma.flowbiz.cloud/healthz
```

**Expected:**

```json
{"status":"ok","service":"dhamma-automation",...}
```

> [!WARNING]
> **STOP IF:** ไม่ได้รับ response หรือ status ไม่ใช่ "ok"

### 2. ตรวจสอบ Meta Endpoint

```bash
curl -fsS https://dhamma.flowbiz.cloud/v1/meta
```

### 3. ตรวจสอบ Docker Container

```bash
cd /opt/flowbiz-client-dhamma
docker compose --env-file config/flowbiz_port.env ps
```

**Expected:** Container `dhamma-web` ต้องแสดงสถานะ `Up`

> [!WARNING]
> **STOP IF:** Container ไม่ running หรือ restarting loop

### 4. ตรวจสอบ Port Binding

```bash
source config/flowbiz_port.env
ss -lntp | grep "${FLOWBIZ_ALLOCATED_PORT}"
```

**Expected:** `127.0.0.1:<port>` (ไม่ใช่ `0.0.0.0:<port>`)

> [!CAUTION]
> **STOP IF:** พบ `0.0.0.0` binding — แก้ไข docker-compose.yml ก่อนดำเนินการต่อ

### 5. ตรวจสอบ Soft-Live ENV (ไม่แสดง secrets)

```bash
grep '^SOFT_LIVE_' .env
```

**Expected Output (ตัวอย่าง):**

```
SOFT_LIVE_ENABLED=true
SOFT_LIVE_YOUTUBE_MODE=dry_run
SOFT_LIVE_FAIL_CLOSED=true
```

### 6. ตรวจสอบ YouTube Credentials (ตรวจแค่การมีอยู่)

```bash
grep -q '^YOUTUBE_CLIENT_ID=' .env && echo "✓ YOUTUBE_CLIENT_ID" || echo "✗ MISSING"
grep -q '^YOUTUBE_CLIENT_SECRET=' .env && echo "✓ YOUTUBE_CLIENT_SECRET" || echo "✗ MISSING"
grep -q '^YOUTUBE_REFRESH_TOKEN=' .env && echo "✓ YOUTUBE_REFRESH_TOKEN" || echo "✗ MISSING"
```

> [!CAUTION]
> **STOP IF:** มี credentials ใดๆ ขาดหายไป — ติดต่อ admin เพื่อเพิ่ม credentials

### 7. ตรวจสอบ YouTube Upload Enabled

```bash
grep -q '^YOUTUBE_UPLOAD_ENABLED=true' .env && echo "✓ YOUTUBE_UPLOAD_ENABLED" || echo "✗ MISSING or false"
```

> [!WARNING]
> **หากขาด:** ต้องเพิ่ม `YOUTUBE_UPLOAD_ENABLED=true` ใน `.env` (ค่า default เป็น `false`)

### 8. ตรวจสอบ youtube_token.json

```bash
ls -la youtube_token.json 2>/dev/null && echo "✓ TOKEN FILE EXISTS" || echo "✗ TOKEN FILE MISSING"
```

> [!CAUTION]
> **หากขาด:** ต้องสร้าง token ผ่าน OAuth flow หรือ copy จากที่อื่น

---

## B) Configure Soft-Live Unlisted Mode

### 1. แก้ไข .env

```bash
cd /opt/flowbiz-client-dhamma
nano .env
```

**ตั้งค่าดังนี้:**

```bash
SOFT_LIVE_ENABLED=true
SOFT_LIVE_YOUTUBE_MODE=unlisted
SOFT_LIVE_FAIL_CLOSED=true
YOUTUBE_UPLOAD_ENABLED=true
```

### 2. Restart Containers

```bash
docker compose --env-file config/flowbiz_port.env up -d --build --remove-orphans
```

### 3. ยืนยัน Health หลัง Restart

```bash
source config/flowbiz_port.env
curl -fsS "http://127.0.0.1:${FLOWBIZ_ALLOCATED_PORT}/healthz"
```

> [!WARNING]
> **STOP IF:** Health check ล้มเหลว — ตรวจสอบ logs ด้วย `docker compose logs --tail 50`

---

## C) Run Pipeline

### 1. กำหนด Run ID

Run ID ต้องมี format: `smoke_unlisted_YYYYMMDD_HHMM`

```bash
RUN_ID="smoke_unlisted_$(date +%Y%m%d_%H%M)"
echo "Run ID: ${RUN_ID}"
```

### 2. Prepare Mock Artifacts (สำคัญ: ต้องทำก่อนรัน)

เนื่องจาก Pipeline `requires_quality` ต้องการไฟล์จากขั้นตอนก่อนหน้า (Production Video Gen) เราต้องสร้าง Mock artifacts ขึ้นมา:

```bash
# 1. สร้างโฟลเดอร์ Artifacts ล่วงหน้า
mkdir -p output/${RUN_ID}/artifacts

# 2. สร้าง Mock Quality Gate Summary (เพื่อให้ Decision Support ผ่าน)
cat > output/${RUN_ID}/artifacts/quality_gate_summary.json << 'EOF'
{
  "run_id": "${RUN_ID}",
  "status": "passed",
  "passed_checks": 3,
  "failed_checks": 0,
  "video_duration_sec": 30,
  "video_size_bytes": 1024000
}
EOF

# 3. Inject Video File (ต้องมีไฟล์วิดีโอจริงเพื่อ Upload)
# ใช้ไฟล์ทดสอบที่มีในเครื่อง หรือสร้าง dummy (ถ้า Youtube API รองรับ) แต่ควรใช้ไฟล์จริง
if [ -f "assets/test_smoke.mp4" ]; then
    cp assets/test_smoke.mp4 output/${RUN_ID}/artifacts/video.mp4
    echo "✓ Injected video.mp4 from assets"
else
    echo "⚠️ WARNING: ไม่พบ assets/test_smoke.mp4"
    echo "กรุณาหาไฟล์ .mp4 มาวางที่: output/${RUN_ID}/artifacts/video.mp4 ก่อน Approve"
fi
```

### 3. รัน Pipeline

> [!NOTE]
> ใช้ `orchestrator.py` (แทน `run_pipeline.py`) เพื่อรองรับ `--run-id`

```bash
cd /opt/flowbiz-client-dhamma
# รันภายใน container เพื่อให้มี fonts และ ffmpeg
docker compose --env-file config/flowbiz_port.env exec web python orchestrator.py \
  --pipeline pipelines/youtube_upload_smoke_requires_quality.yaml \
  --run-id "${RUN_ID}"
```

### 4. Output Location

Artifacts จะถูกสร้างที่:

```
output/<run_id>/artifacts/
output/<run_id>/control/
```

---

## D) Approval Gate Handling

### ระบบ Approval Gate

Pipeline ใช้ระบบ **timeout-based auto-approve**:

- Grace period: **2 ชั่วโมง** (120 นาที)
- หากไม่มีการ cancel ภายใน 2 ชม. → **approved_by_timeout**
- หากต้องการ cancel → สร้าง cancel file
- **หากตรวจสอบทุกอย่างครบแล้ว สามารถ force approve ได้โดยรอเวลา (หรือแก้ config dev)**

### ⚠️ Double Check: Video File

ตรวจสอบว่ามีไฟล์วิดีโอใน artifacts แล้วหรือยัง (เราทำในขั้นตอน C.2 แล้ว แต่เช็คอีกที):

```bash
ls -l output/${RUN_ID}/artifacts/video.mp4
```

> [!IMPORTANT]
> ต้องมีไฟล์ `video.mp4` ก่อนที่ Pipeline จะเริ่มขั้นตอน Upload (หลัง Approved)

### ตรวจสอบสถานะ Approval Gate

```bash
cat output/${RUN_ID}/artifacts/approval_gate_summary.json | jq '.status'
```

| Status | ความหมาย |
|--------|----------|
| `pending` | รอ grace period (pipeline จะ HOLD) |
| `approved_by_timeout` | หมดเวลา 2 ชม. ดำเนินต่อได้ |
| `rejected` | ถูก cancel แล้ว |

### วิธี Approve (รอ Timeout)

หาก status เป็น `pending`:

1. **รอ** จนกว่า grace period หมด (สูงสุด 2 ชม.)
2. ตรวจสอบว่าไม่มีไฟล์ cancel:

   ```bash
   [ -f "output/${RUN_ID}/control/cancel_publish.json" ] && echo "CANCEL EXISTS" || echo "OK - No cancel"
   ```

3. รัน pipeline อีกครั้งหรือรอ orchestrator retry

### วิธี Cancel (สร้าง Cancel File)

หากต้องการยกเลิก:

```bash
mkdir -p output/${RUN_ID}/control
cat > output/${RUN_ID}/control/cancel_publish.json << 'EOF'
{
  "action": "cancel_publish",
  "actor": "<YOUR_NAME>",
  "reason": "<REASON_FOR_CANCEL>"
}
EOF
```

> [!IMPORTANT]
> หลังสร้าง cancel file แล้ว pipeline จะ reject ทันทีในรอบถัดไป

---

## E) Success Criteria

### 1. ตรวจสอบ Artifacts

```bash
ls -la output/${RUN_ID}/artifacts/
```

**ต้องมีไฟล์:**

- `approval_gate_summary.json`
- `soft_live_summary.json`
- `youtube_upload_summary.json`

### 2. ตรวจสอบ Soft-Live Summary

```bash
cat output/${RUN_ID}/artifacts/soft_live_summary.json | jq '.enforced_mode'
```

**Expected:** `"unlisted"`

### 3. ตรวจสอบ Video ID

```bash
cat output/${RUN_ID}/artifacts/youtube_upload_summary.json | jq '.video_id'
```

**Success Criteria:**

- ✅ Video ID ต้อง **ไม่** ขึ้นต้นด้วย `fake-`
- ✅ Video ID ต้อง **ไม่** ขึ้นต้นด้วย `soft-live-dry-`
- ✅ Video ID ต้องเป็น YouTube ID format (11 ตัวอักษร)

### 4. ตรวจสอบ Logs

```bash
docker compose --env-file config/flowbiz_port.env logs --tail 200 | grep -i "soft-live"
```

**Expected:** พบ `Soft-Live Enabled. Mode: unlisted`

### 5. ทดสอบเปิด Video

เปิด URL: `https://www.youtube.com/watch?v=<VIDEO_ID>`

- ✅ ต้องเปิดได้เมื่อมี link
- ✅ ต้องไม่ปรากฏใน YouTube search (unlisted)

---

## F) Evidence Collection (Audit)

### 1. สร้าง Evidence Bundle

```bash
EVIDENCE_DIR="output/${RUN_ID}/evidence_$(date +%Y%m%d_%H%M%S)"
mkdir -p "${EVIDENCE_DIR}"

# Copy artifacts
cp output/${RUN_ID}/artifacts/* "${EVIDENCE_DIR}/"

# Export logs
docker compose --env-file config/flowbiz_port.env logs --tail 200 > "${EVIDENCE_DIR}/docker_logs.txt"

# Export health checks
curl -fsS https://dhamma.flowbiz.cloud/healthz > "${EVIDENCE_DIR}/healthz.json"
curl -fsS https://dhamma.flowbiz.cloud/v1/meta > "${EVIDENCE_DIR}/meta.json"

# Export container status
docker compose --env-file config/flowbiz_port.env ps > "${EVIDENCE_DIR}/docker_ps.txt"

echo "Evidence collected at: ${EVIDENCE_DIR}"
```

### 2. รายการ Evidence

| Item | Path |
|------|------|
| Approval Gate Summary | `evidence_*/approval_gate_summary.json` |
| Soft-Live Summary | `evidence_*/soft_live_summary.json` |
| YouTube Upload Summary | `evidence_*/youtube_upload_summary.json` |
| Docker Logs | `evidence_*/docker_logs.txt` |
| Health Check | `evidence_*/healthz.json` |
| Meta | `evidence_*/meta.json` |
| Container Status | `evidence_*/docker_ps.txt` |

---

## G) Rollback to Safe State

> [!IMPORTANT]
> **หลังทดสอบเสร็จต้อง rollback กลับไป dry_run เสมอ**

### 1. แก้ไข .env

```bash
cd /opt/flowbiz-client-dhamma
nano .env
```

**ตั้งค่ากลับ:**

```bash
SOFT_LIVE_YOUTUBE_MODE=dry_run
```

### 2. Restart Containers

```bash
docker compose --env-file config/flowbiz_port.env up -d --remove-orphans
```

### 3. ยืนยัน Health

```bash
source config/flowbiz_port.env
curl -fsS "http://127.0.0.1:${FLOWBIZ_ALLOCATED_PORT}/healthz"
```

### 4. ยืนยันว่า dry_run ใช้งานได้

```bash
grep '^SOFT_LIVE_YOUTUBE_MODE=' .env
# Expected: SOFT_LIVE_YOUTUBE_MODE=dry_run
```

---

## H) Troubleshooting

### Missing Credentials

**อาการ:** Pipeline ล้มเหลวด้วย error เกี่ยวกับ credentials

**แก้ไข:**

1. ตรวจสอบ `.env` มี keys ครบ: `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REFRESH_TOKEN`
2. ติดต่อ admin เพื่อเพิ่ม credentials ที่ขาด
3. Restart containers หลังแก้ไข

### Token Expired

**อาการ:** Error `invalid_grant` หรือ `Token has been revoked`

**แก้ไข:**

1. สร้าง refresh token ใหม่ผ่าน OAuth flow
2. อัปเดต `YOUTUBE_REFRESH_TOKEN` ใน `.env`
3. Restart containers

### YouTube API Quota / 403

**อาการ:** Error `quotaExceeded` หรือ `403 Forbidden`

**แก้ไข:**

1. ตรวจสอบ quota ใน Google Cloud Console
2. รอ 24 ชม. หาก quota หมด
3. หาก 403: ตรวจสอบ API permissions ใน Google Cloud Console

### Upload Fails but Pipeline Continues

**อาการ:** Pipeline สำเร็จแต่ไม่มี video_id จริง

**แก้ไข:**

1. ตรวจสอบ `soft_live_summary.json` ว่า `enforced_mode` ถูกต้อง
2. ตรวจสอบ `youtube_upload_summary.json` หา error messages
3. ดู docker logs สำหรับ stack trace

### Approval Gate Stuck in Pending

**อาการ:** Pipeline HOLD ไม่ดำเนินต่อ

**แก้ไข:**

1. ตรวจสอบ `approval_gate_summary.json` ว่า `opened_at_utc` เวลาใด
2. หาก grace period ยังไม่หมด: รอ หรือ สร้าง cancel file เพื่อยกเลิก
3. หาก grace period หมดแล้ว: รัน pipeline อีกครั้ง

---

## Related Docs

| Document | Purpose |
|----------|---------|
| [RUNBOOK_VPS_PRODUCTION.md](./RUNBOOK_VPS_PRODUCTION.md) | VPS operations runbook หลัก |
| [approval_gate_summary_v1.md](./contracts/approval_gate_summary_v1.md) | Approval gate artifact schema |
| [soft_live_summary_v1.md](./contracts/soft_live_summary_v1.md) | Soft-live artifact schema |
