# VPS Production Runbook

> **Single source of truth** สำหรับการ deploy, operate, และ recover บน FlowBiz VPS

---

## 1. Scope & Safety Rules

### ขอบเขต

เอกสารนี้ครอบคลุม:

- การ deploy แบบ manual บน VPS
- การ deploy อัตโนมัติผ่าน GitHub Actions (Gated)
- การ operate และ monitor service
- การ rollback และ recovery (Manual & CI-trigger)
- Approval gate operations
- Soft-live mode operations

เอกสารนี้ **ไม่ครอบคลุม**:

- DNS/Domain configuration
- Firewall rules
- Log aggregation (ELK/Grafana)
- Secrets rotation automation

### กฎความปลอดภัย (Never Do List)

> [!CAUTION]
> **ห้ามทำสิ่งต่อไปนี้โดยเด็ดขาด:**

| ❌ ห้าม | เหตุผล |
|--------|--------|
| ใช้ `0.0.0.0` binding | เปิด port สู่ internet โดยตรง |
| Paste secrets ลง repo | ความปลอดภัยของข้อมูล |
| Bypass approval gate โดยไม่มีเอกสาร | Audit trail |
| รัน `preflight.sh` บน VPS | ใช้สำหรับ CI เท่านั้น (ต้องการ Python 3.11+, รัน tests) |
| ใช้ docker compose โดยไม่มี `--env-file` | Port config จะไม่ถูกโหลด |

---

## 2. Production Topology

### Paths

| Purpose | Path |
|---------|------|
| Application | `/opt/flowbiz-client-dhamma` |
| Data | `/opt/flowbiz-client-dhamma/data` |
| Output | `/opt/flowbiz-client-dhamma/output` |
| Control artifacts | `/opt/flowbiz-client-dhamma/output/<run_id>/control/` |
| Approval artifacts | `/opt/flowbiz-client-dhamma/output/<run_id>/artifacts/` |

### Ports

| Component | Port | Binding |
|-----------|------|---------|
| Container internal | 8000 | - |
| Host binding | ${FLOWBIZ_ALLOCATED_PORT} | 127.0.0.1 only |
| Default port | 3007 | จาก config/flowbiz_port.env |
| Nginx HTTP | 80 | Public |
| Nginx HTTPS | 443 | Public |

### Architecture Diagram

```
┌─────────────────┐      ┌─────────────────────┐      ┌──────────────────┐
│   Internet      │──────│  System Nginx       │──────│  Docker Container │
│                 │ :443 │  127.0.0.1:3007     │ :3007│  :8000           │
└─────────────────┘      └─────────────────────┘      └──────────────────┘
        │                         │                           │
        │                         │                           │
   TLS termination           Reverse proxy              FastAPI app
   (Let's Encrypt)           (host nginx)               (dhamma-web)
```

---

## 3. Prerequisites (VPS)

### Required

- [ ] Docker 20.10+ with compose plugin

  ```bash
  docker compose version
  # OR legacy: docker-compose --version
  ```

- [ ] nginx installed on host

  ```bash
  sudo apt install nginx
  ```

- [ ] git installed

  ```bash
  git --version
  ```

- [ ] curl installed

  ```bash
  curl --version
  ```

- [ ] Disk space minimum 5GB free

  ```bash
  df -h /opt
  ```

- [ ] `config/flowbiz_port.env` exists with `FLOWBIZ_ALLOCATED_PORT` set

### Optional

- [ ] jq (for health check JSON parsing)

  ```bash
  sudo apt install jq
  ```

- [ ] Python 3.11+ (required if running pipelines manually on VPS)

  ```bash
  python3 --version
  ```

---

## 4. One-Time Setup (First Deploy)

> [!IMPORTANT]
> **AUDIT REQUIREMENT**: This setup MUST be performed manually by a human operator.
> **DO NOT** use automated scripts that SSH into production servers.
> Every command executed must be auditable and performed explicitly.

### 4.1 Create folder

```bash
sudo mkdir -p /opt/flowbiz-client-dhamma
cd /opt
```

### 4.2 Clone repo

```bash
sudo git clone https://github.com/01bkgift/flowbiz-client-dhamma.git flowbiz-client-dhamma && sudo chown -R $(whoami):$(whoami) flowbiz-client-dhamma
cd flowbiz-client-dhamma
```

### 4.3 Create .env from template

```bash
sudo cp .env.example .env
sudo nano .env  # แก้ไขค่าตามต้องการ
```

### 4.4 Verify port config

```bash
cat config/flowbiz_port.env
# Expected: FLOWBIZ_ALLOCATED_PORT=3007
```

> [!WARNING]
> **STOP IF:** ไฟล์ไม่มีอยู่หรือ FLOWBIZ_ALLOCATED_PORT ว่างเปล่า

### 4.5 Verify compose binds to 127.0.0.1

```bash
grep -E "127\.0\.0\.1.*:8000" docker-compose.yml
```

> [!WARNING]
> **STOP IF:** ไม่พบ pattern ที่ตรงกัน

### 4.6 Install nginx site config

```bash
sudo cp nginx/dhamma-automation.conf /etc/nginx/sites-available/
sudo nano /etc/nginx/sites-available/dhamma-automation.conf
# แก้ไข:
# - DOMAIN_NAME → domain จริง
# - ตรวจสอบ upstream port ตรงกับ FLOWBIZ_ALLOCATED_PORT

sudo ln -s /etc/nginx/sites-available/dhamma-automation.conf /etc/nginx/sites-enabled/
```

### 4.7 Test and reload nginx

```bash
sudo nginx -t
```

> [!CAUTION]
> **STOP IF:** nginx -t fails — แก้ config ก่อนดำเนินการต่อ

```bash
sudo systemctl reload nginx
```

---

## 5. CI/CD Deployment (Automated & Gated)

สิทธิ์การ deploy ถูกควบคุมผ่าน GitHub Actions และ GitHub Environment Protection

### 5.1 Workflow Triggers

- **Manual Trigger:** ผ่าน GitHub UI (Actions tab -> Deploy to VPS)
- **Inputs:**
  - `ref`: Branch หรือ SHA ที่ต้องการ deploy
  - `action`: `deploy` หรือ `rollback`
  - `rollback_sha`: SHA ที่ต้องการกลับไป (ใช้เฉพาะ action=rollback)

### 5.2 Approval Gate

- การ deploy ไปยัง `production` จะต้องได้รับการ approve จาก **Reviewer** ที่ระบุใน GitHub Environment settings เท่านั้น
- Workflow จะ HOLD จนกว่าจะมีการ Approve หรือ Timeout (7 days)

### 5.3 Deterministic Deployment

- CI จะ resolve `ref` เป็น SHA-1 ก่อนเริ่ม deploy
- CI จะเชื่อมต่อ VPS ผ่าน SSH (`StrictHostKeyChecking=yes`)
- CI จะรัน `git reset --hard <SHA>` บน VPS เพื่อความถูกต้องแม่นยำ

### 5.4 Rollback via CI

1. ไปที่ GitHub Actions -> "Deploy to VPS (Gated)"
2. เลือก Action: `rollback`
3. ใส่ SHA ที่ต้องการกลับไปใน `rollback_sha`
4. Approve และรอ CI ติตตั้งกลับคืน

---

## 6. Standard Deploy (Manual)

### 6.1 Commands

```bash
cd /opt/flowbiz-client-dhamma

# Fetch latest
git fetch --all --prune
git checkout main
git reset --hard origin/main

# Run deploy verification (ไม่ใช่ preflight.sh)
bash scripts/runtime_verify.sh

# Start containers
docker compose --env-file config/flowbiz_port.env up -d --remove-orphans

# Verify containers running
docker compose --env-file config/flowbiz_port.env ps
```

### 5.2 Health Check

```bash
source config/flowbiz_port.env
curl -fsS "http://127.0.0.1:${FLOWBIZ_ALLOCATED_PORT}/healthz"
```

Expected response:

```json
{"status":"ok","service":"dhamma-automation","version":"..."}
```

Alternative (with jq):

```bash
curl -fsS "http://127.0.0.1:${FLOWBIZ_ALLOCATED_PORT}/healthz" | jq -r '.status'
# Expected: ok
```

### 5.3 Port Verification

```bash
ss -lntp | grep "${FLOWBIZ_ALLOCATED_PORT}"
# Expected: LISTEN on 127.0.0.1:<port>
```

### 5.4 STOP Conditions

| Condition | Action |
|-----------|--------|
| `runtime_verify.sh` returns non-zero | หยุด, ตรวจสอบ error |
| `docker compose ps` shows 0 containers | หยุด, ตรวจสอบ logs |
| Port not listening | หยุด, ตรวจสอบ container |
| curl /healthz returns non-200 | หยุด, ตรวจสอบ app logs |
| nginx upstream port ไม่ตรง | หยุด, แก้ nginx config |

---

## 6. How to Run Pipelines on VPS (Manual)

### Command

```bash
cd /opt/flowbiz-client-dhamma
python scripts/run_pipeline.py --pipeline pipelines/youtube_upload_smoke_requires_quality.yaml
```

### Expected Behavior

- Approval gate อาจ HOLD (ตรวจสอบ exit code และ summary.json)
- Soft-live mode ขึ้นกับ env vars

### Smoke Checklist

1. ตั้ง `SOFT_LIVE_ENABLED=true` ใน .env
2. ตั้ง `SOFT_LIVE_YOUTUBE_MODE=dry_run` ใน .env
3. Run pipeline
4. ✅ ยืนยัน: approval gate สร้าง `output/<run_id>/artifacts/approval_gate_summary.json`
5. ✅ ยืนยัน: soft-live สร้าง fake video ID (format: `fake-xxxxxxxx-xxxx-...`)
6. ✅ ยืนยัน: ไม่มีการ publish สาธารณะระหว่าง smoke test

---

## 7. Approval Gate Operations

### Artifact Locations

| Type | Path |
|------|------|
| Approval summary | `output/<run_id>/artifacts/approval_gate_summary.json` |
| Cancel file | `output/<run_id>/control/cancel_publish.json` |

### How to Cancel Manually

```bash
mkdir -p output/<run_id>/control
cat > output/<run_id>/control/cancel_publish.json << 'EOF'
{
  "action": "cancel_publish",
  "actor": "<YOUR_NAME>",
  "reason": "<REASON>"
}
EOF
```

### Decision Semantics

| Status | Description |
|--------|-------------|
| `pending` | รอการตัดสินใจ |
| `approved_by_timeout` | ไม่มี cancel file, หมดเวลา timeout |
| `rejected` | พบ cancel_publish.json ที่มี action ถูกต้อง |

---

## 8. Soft-Live Operations

### Environment Variables

| Variable | Values | Default | Description |
|----------|--------|---------|-------------|
| `SOFT_LIVE_ENABLED` | true/false | true | เปิด/ปิด soft-live mode |
| `SOFT_LIVE_YOUTUBE_MODE` | dry_run/unlisted/public | dry_run | โหมดการ upload |
| `SOFT_LIVE_FAIL_CLOSED` | true/false | true | Fail หาก config ไม่ถูกต้อง |

### Mode Behaviors

| Mode | Behavior |
|------|----------|
| `dry_run` | ไม่เรียก YouTube API, return fake video ID, log "DRY_RUN: would upload..." |
| `unlisted` | Upload จริง, ตั้ง visibility เป็น "unlisted", return video ID จริง |
| `public` | **อันตราย**: Publish สาธารณะจริง, ใช้เมื่อ approval gate approved เท่านั้น |

### Fake Video ID Format

- Pattern: `fake-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`
- Derived from normalized content fingerprint
- Stable across re-runs for the same content + mode
- Deterministic fake video ID

---

## 9. Logs & Troubleshooting

### View Logs

```bash
# Container logs
docker compose --env-file config/flowbiz_port.env logs -f
docker compose --env-file config/flowbiz_port.env logs --tail 100

# Nginx logs
sudo tail -f /var/log/nginx/dhamma-access.log
sudo tail -f /var/log/nginx/dhamma-error.log
```

### Common Failures

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| Container exits immediately | Missing .env หรือ bad port | ตรวจ docker logs, verify .env |
| Port already in use | Service อื่นใช้ port | `lsof -i :<port>`, เปลี่ยน port |
| nginx 502 Bad Gateway | Container not running | `docker compose up -d` |
| curl: connection refused | Container ไม่ listen 127.0.0.1 | Verify docker-compose.yml ports |

### Safe First Principle

- ✅ รัน `scripts/runtime_verify.sh` ก่อนและหลังการเปลี่ยนแปลงเสมอ
- ✅ ตรวจ logs ก่อน restart

---

## 10. Rollback

### 10.1 Identify last good commit

```bash
git log -n 10 --oneline
```

### 10.2 Reset to SHA

```bash
git reset --hard <KNOWN_GOOD_SHA>
```

### 10.3 Restart compose

```bash
docker compose --env-file config/flowbiz_port.env up -d --remove-orphans
```

### 10.4 Verify

```bash
bash scripts/runtime_verify.sh
```

> [!WARNING]
> **STOP IF:** runtime_verify.sh returns non-zero

---

## 11. Recovery

### Disk Full

```bash
# Check disk usage
df -h
du -sh /opt/dhamma-channel-automation/output/*

# Clean old outputs (CAUTION: audit implications)
# ลบเฉพาะหลังจาก backup/archive แล้วเท่านั้น
cd /opt/flowbiz-client-dhamma/output && rm -rf ./<old_run_id>
```

### Nginx Broken

```bash
sudo nginx -t  # หา syntax errors
sudo systemctl status nginx
sudo journalctl -u nginx --since "1 hour ago"
```

### Compose Broken

```bash
docker compose --env-file config/flowbiz_port.env down
docker compose --env-file config/flowbiz_port.env up -d
```

### Secrets Rotated

1. Update .env with new values
2. Restart compose
3. **ห้าม commit .env ลง repo**

---

## 12. Audit & Evidence (SOC2/ISO)

### What to Retain

- `output/<run_id>/artifacts/*` (approval gate summaries)
- `output/<run_id>/control/*` (cancel decisions)
- Docker container logs
- nginx access/error logs
- Deploy logs (git log, compose output)

### Minimum Retention

> [!IMPORTANT]
> **Recommendation:** 90 วันขั้นต่ำ  
> ปรับตาม SOC2 audit requirements ขององค์กร  
> เอกสารนี้ไม่ใช่คำแนะนำทางกฎหมาย

### Evidence Collection

```bash
# Export recent deploy logs
git log --since="30 days ago" --oneline > deploy_history.txt

# Export container logs
docker compose --env-file config/flowbiz_port.env logs --since 720h > container_logs.txt
```

---

## Related Docs

| Doc | Description |
|---|---|
| [**RUNBOOK_VPS_PRODUCTION.md**](./RUNBOOK_VPS_PRODUCTION.md) | Single source of truth สำหรับ deploy/operate/recover |
| [RUNBOOK_SOFT_LIVE_UNLISTED_VERIFY.md](./RUNBOOK_SOFT_LIVE_UNLISTED_VERIFY.md) | Runbook สำหรับ verify Soft-Live unlisted mode |
| [DEPLOYMENT_FLOWBIZ_VPS.md](./DEPLOYMENT_FLOWBIZ_VPS.md) | VPS architecture overview |
| [OPS_CHECKLIST.md](./OPS_CHECKLIST.md) | Daily/weekly ops checklist |
| [SECURITY_DEPLOYMENT_NOTES.md](./SECURITY_DEPLOYMENT_NOTES.md) | SOC2/ISO security notes |
| [.github/workflows/deploy-vps.yml](../.github/workflows/deploy-vps.yml) | GitHub Actions CI/CD workflow |

---

## 13. Appendix: SSH Access Setup

สำหรับ Developer หรือ Agent ที่ต้องการ SSH เข้า VPS (ต้องได้รับอนุญาตและมี Key)

**ข้อมูล SSH:**

- **Hostname/IP:** <VPS_IP_ADDRESS>
- **SSH Port:** 22
- **User:** <your_user>
- **Identity File:** `~/.ssh/id_ed25519_flowbiz` (Ed25519)

**การตั้งค่า `~/.ssh/config` (Recommended):**

เพิ่มเนื้อหาต่อไปนี้ลงในไฟล์ `~/.ssh/config` ของคุณ:

```ssh
Host flowbiz-vps
  HostName <VPS_IP_ADDRESS>
  User <your_user>
  Port 22
  IdentityFile ~/.ssh/id_ed25519_flowbiz
  StrictHostKeyChecking yes
```

**การใช้งาน:**

```bash
ssh flowbiz-vps
```
