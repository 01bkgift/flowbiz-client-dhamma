# Security Deployment Notes

> SOC2/ISO compliant security notes สำหรับ VPS deployment

---

## Access Control

### SSH Access

| Requirement | Status |
|-------------|--------|
| SSH key authentication | ✅ Required |
| Password authentication | ❌ Disabled |
| Root login | ❌ Disabled |
| Sudo access | ✅ Required for docker/nginx |

### Recommended SSH Setup

```bash
# บน local machine
ssh-keygen -t ed25519 -C "deploy@dhamma-automation"

# Copy to server
ssh-copy-id -i ~/.ssh/id_ed25519.pub user@vps-host

# บน server - disable password auth
sudo nano /etc/ssh/sshd_config
# PasswordAuthentication no
# PermitRootLogin no

sudo systemctl restart sshd
```

### Access Levels

| Role | Access | Scope |
|------|--------|-------|
| Deploy operator | sudo | docker, nginx, git operations |
| Viewer | read-only | logs, status checks only |
| Application | container | internal app only |

---

## Least Privilege

### Docker

- Container runs with minimal capabilities
- No `--privileged` flag
- Network restricted to localhost binding

### Nginx

- Runs as `www-data` user
- Only ports 80, 443 exposed
- No access to application internals

### Application

- No direct internet exposure
- All traffic via nginx reverse proxy
- Secrets in .env only (not in repo)

---

## Secrets Management

### ห้ามทำ

| ❌ Never | เหตุผล |
|----------|--------|
| Commit secrets to repo | Git history is permanent |
| Hardcode in Dockerfile | Image layers visible |
| Log secrets | Log files may be shared |
| Share .env file | One secret = one owner |

### ต้องทำ

| ✅ Must | วิธี |
|---------|-----|
| Use .env file | Server-side only |
| Rotate regularly | Quarterly minimum |
| Audit access | Log who accesses what |
| Encrypt at rest | Use encrypted volumes if possible |

### Files to Protect

```bash
# These files must NEVER be committed
.env
*.pem
*.key
*_secret*.json
youtube_token.json
client_secret.json
```

Verify in `.gitignore`:

```bash
grep -E "\.env|secret|token|\.pem|\.key" .gitignore
```

---

## Audit Trail

### What Gets Logged

| Event | Location | Retention |
|-------|----------|-----------|
| SSH access | `/var/log/auth.log` | 90+ days |
| nginx access | `/var/log/nginx/dhamma-access.log` | 90+ days |
| nginx errors | `/var/log/nginx/dhamma-error.log` | 90+ days |
| Container logs | `docker logs dhamma-web` | 90+ days |
| Deploy history | `git log` | Permanent |
| Approval decisions | `output/<run_id>/artifacts/` | 90+ days |
| Cancel actions | `output/<run_id>/control/` | 90+ days |

### Log Export for Audit

```bash
# Export logs for audit period
AUDIT_START="2025-01-01"
AUDIT_END="2025-03-31"

# Git history
git log --since="${AUDIT_START}" --until="${AUDIT_END}" \
  --format="%H|%ai|%an|%s" > audit_git.csv

# Docker logs (last 90 days)
docker compose --env-file config/flowbiz_port.env logs \
  --since 2160h > audit_container.log

# Nginx logs
sudo cp /var/log/nginx/dhamma-access.log* audit/
```

---

## Log Retention

### Minimum Retention Windows

| Log Type | Minimum Retention | Reason |
|----------|-------------------|--------|
| Access logs | 90 days | SOC2 typical audit window |
| Error logs | 90 days | Incident investigation |
| Deploy logs | 1 year | Change management |
| Approval artifacts | 1 year | Decision audit |

### Log Rotation

nginx logs ถูก rotate อัตโนมัติโดย logrotate:

```bash
cat /etc/logrotate.d/nginx
```

Docker logs rotation:

```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "100m",
    "max-file": "5"
  }
}
```

---

## Network Security

### Port Exposure

| Port | Binding | Purpose |
|------|---------|---------|
| 22 | 0.0.0.0 | SSH (with key auth) |
| 80 | 0.0.0.0 | HTTP (redirects to HTTPS) |
| 443 | 0.0.0.0 | HTTPS (nginx) |
| 3007 | 127.0.0.1 | Application (internal only) |

### Firewall Rules (UFW Example)

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### Verification

```bash
# Verify app not exposed directly
ss -lntp | grep 3007
# Should show: 127.0.0.1:3007 ONLY

# Verify from external (should fail)
# curl http://<server-ip>:3007/healthz
# Expected: Connection refused
```

---

## Incident Response

### If Secrets Leaked

1. **Immediate**: Rotate all affected secrets
2. **Revoke**: Invalidate old tokens/keys
3. **Audit**: Check access logs for unauthorized use
4. **Document**: Record incident timeline
5. **Review**: Update procedures to prevent recurrence

### If Unauthorized Access Detected

1. **Block**: Disable SSH access for affected key
2. **Investigate**: Review auth.log for access pattern
3. **Contain**: Stop affected containers if needed
4. **Report**: Document per incident policy
5. **Remediate**: Change all secrets, review access

---

## Compliance Checklist

### SOC2 Trust Principles

| Principle | Implementation |
|-----------|----------------|
| Security | SSH key auth, firewall, localhost binding |
| Availability | Health checks, restart policy |
| Processing Integrity | Approval gate, audit logs |
| Confidentiality | Secrets in .env, TLS |
| Privacy | No PII logging |

### ISO 27001 Relevant Controls

| Control | Implementation |
|---------|----------------|
| A.9.4.1 | SSH key authentication |
| A.12.4.1 | Event logging (nginx, docker) |
| A.12.4.3 | Log protection (logrotate) |
| A.13.1.1 | Network segmentation (localhost only) |
| A.14.1.2 | TLS for all external traffic |

---

## Related Docs

- [RUNBOOK_VPS_PRODUCTION.md](./RUNBOOK_VPS_PRODUCTION.md) — Full runbook
- [OPS_CHECKLIST.md](./OPS_CHECKLIST.md) — Daily/weekly checklist
- [GUARDRAILS.md](./GUARDRAILS.md) — Automated compliance checks
