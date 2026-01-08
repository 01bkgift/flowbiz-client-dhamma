# Ops Checklist

> Checklist สำหรับการตรวจสอบ production ประจำวัน/สัปดาห์

---

## Daily Checklist

### 1. Container Health

```bash
cd /opt/dhamma-channel-automation
docker compose --env-file config/flowbiz_port.env ps
```

- [ ] Container status: `Up`
- [ ] No restart loops

### 2. Health Endpoint

```bash
source config/flowbiz_port.env
curl -fsS "http://127.0.0.1:${FLOWBIZ_ALLOCATED_PORT}/healthz"
```

- [ ] Returns `{"status":"ok",...}`
- [ ] Response time < 2 seconds

### 3. Nginx Status

```bash
sudo systemctl status nginx
```

- [ ] Status: `active (running)`
- [ ] No recent errors

### 4. Quick Log Review

```bash
docker compose --env-file config/flowbiz_port.env logs --tail 50 | grep -iE "error|fail|exception"
```

- [ ] No critical errors
- [ ] No unexpected exceptions

---

## Weekly Checklist

### 1. Disk Space

```bash
df -h /opt
du -sh /opt/dhamma-channel-automation/output
du -sh /opt/dhamma-channel-automation/data
```

- [ ] Disk usage < 80%
- [ ] Output directory growth is expected
- [ ] Data directory size is reasonable

### 2. Output Cleanup Assessment

```bash
ls -la /opt/dhamma-channel-automation/output | head -20
find /opt/dhamma-channel-automation/output -maxdepth 1 -type d -mtime +30 | wc -l
```

- [ ] Review old outputs (>30 days)
- [ ] Archive if needed before deletion
- [ ] Document any deletions for audit

### 3. Container Resource Usage

```bash
docker stats --no-stream dhamma-web
```

- [ ] Memory usage reasonable
- [ ] CPU not pegged at 100%

### 4. Nginx Logs Review

```bash
sudo tail -100 /var/log/nginx/dhamma-error.log
sudo grep -c "502" /var/log/nginx/dhamma-access.log
```

- [ ] No repeated 502 errors
- [ ] No unusual error patterns

### 5. Guardrails Check

```bash
cd /opt/dhamma-channel-automation
bash scripts/guardrails.sh
```

- [ ] All checks pass or warnings documented

---

## Monthly Checklist

### 1. SSL Certificate

```bash
sudo certbot certificates
```

- [ ] Certificate valid > 30 days
- [ ] Auto-renewal working

### 2. Security Updates

```bash
sudo apt update
apt list --upgradable | grep -E "docker|nginx|openssl"
```

- [ ] Review available updates
- [ ] Schedule update window if needed

### 3. Backup Verification

```bash
# Verify backup locations
ls -la /path/to/backups/  # Replace with actual backup path
```

- [ ] Recent backup exists
- [ ] Backup file size reasonable

### 4. Audit Log Export

```bash
cd /opt/dhamma-channel-automation
git log --since="30 days ago" --oneline > /tmp/deploy_history.txt
docker compose --env-file config/flowbiz_port.env logs --since 720h > /tmp/container_logs.txt
```

- [ ] Deploy history exported
- [ ] Container logs archived
- [ ] Stored in audit-compliant location

---

## Policy Compliance Evidence

### สิ่งที่ต้องเก็บ

| Item | Location | Retention |
|------|----------|-----------|
| Approval summaries | `output/<run_id>/artifacts/` | 90+ days |
| Cancel decisions | `output/<run_id>/control/` | 90+ days |
| Deploy history | git log | Permanent |
| Container logs | docker logs | 90+ days |
| Nginx logs | `/var/log/nginx/` | 90+ days |

### Monthly Export Script

```bash
#!/bin/bash
# Run monthly for audit compliance
DATE=$(date +%Y%m)
EXPORT_DIR="/opt/dhamma-channel-automation/audit/${DATE}"
mkdir -p "${EXPORT_DIR}"

# Export git history
git log --since="30 days ago" --format="%H|%ai|%an|%s" > "${EXPORT_DIR}/git_history.csv"

# Export container logs
docker compose --env-file config/flowbiz_port.env logs --since 720h > "${EXPORT_DIR}/container.log"

# Copy approval artifacts
find output -name "approval_gate_summary.json" -mtime -30 -exec cp --parents {} "${EXPORT_DIR}/" \;

echo "Export complete: ${EXPORT_DIR}"
```

---

## Quick Reference

### Commands Summary

| Action | Command |
|--------|---------|
| Check container | `docker compose --env-file config/flowbiz_port.env ps` |
| Check health | `source config/flowbiz_port.env && curl "http://127.0.0.1:${FLOWBIZ_ALLOCATED_PORT}/healthz"` |
| View logs | `docker compose --env-file config/flowbiz_port.env logs -f` |
| Check disk | `df -h /opt` |
| Check nginx | `sudo nginx -t && sudo systemctl status nginx` |
| Run guardrails | `bash scripts/guardrails.sh` |

---

## Related Docs

- [RUNBOOK_VPS_PRODUCTION.md](./RUNBOOK_VPS_PRODUCTION.md) — Full runbook
- [SECURITY_DEPLOYMENT_NOTES.md](./SECURITY_DEPLOYMENT_NOTES.md) — Security notes
