# Deployment Guide

## Overview

This guide covers production deployment of the Dhamma Channel Automation service as a FlowBiz Client Product on a VPS environment.

## Port Allocation

**FLOWBIZ_ALLOCATED_PORT** is defined in `config/flowbiz_port.env` (single source of truth).

This port is registered in the FlowBiz VPS port allocation registry:
- [VPS Status Document](https://github.com/natbkgift/flowbiz-ai-core/blob/main/docs/VPS_STATUS.md)

**Port Conflict Check**:
Before deploying, verify the allocated port is available:
```bash
source config/flowbiz_port.env
sudo lsof -i :"${FLOWBIZ_ALLOCATED_PORT}"
netstat -tulpn | grep "${FLOWBIZ_ALLOCATED_PORT}"
```

If the allocated port is in use, select the nearest available port within range 3001-3099 and update:
- `config/flowbiz_port.env` (single source of truth)
- Run Docker Compose with `--env-file config/flowbiz_port.env` so port binding uses the same value
- Update `nginx/dhamma-automation.conf` to proxy to the port from `config/flowbiz_port.env`

## System Nginx Architecture

### Overview

This project follows the **System Nginx** architecture as defined in:
- [ADR: System Nginx](https://github.com/natbkgift/flowbiz-ai-core/blob/main/docs/ADR_SYSTEM_NGINX.md)
- [System Nginx Operational Guide](https://github.com/natbkgift/flowbiz-ai-core/blob/main/docs/CODEX_SYSTEM_NGINX_FIRST.md)

### Key Principles

1. **Single System Nginx** on VPS (host-level)
   - Installed via `apt install nginx`
   - Runs directly on host, NOT in Docker
   - Listens on ports 80 (HTTP) and 443 (HTTPS)

2. **Client Service Localhost Binding**
   - Service binds ONLY to `127.0.0.1:${FLOWBIZ_ALLOCATED_PORT}`
   - NO public exposure of application ports
   - System Nginx proxies to `http://127.0.0.1:${FLOWBIZ_ALLOCATED_PORT}`

3. **One Domain = One Config File**
   - Config: `/etc/nginx/sites-available/dhamma-automation.conf`
   - Symlink: `/etc/nginx/sites-enabled/dhamma-automation.conf`
   - TLS via Let's Encrypt certbot on host

4. **Security**
   - NO Docker nginx containers for public traffic
   - NO `0.0.0.0` bindings
   - NO port exposure to internet except via System Nginx

## Prerequisites

### Server Requirements
- Ubuntu 20.04+ or Debian 11+
- Docker 20.10+ and Docker Compose
- Nginx installed on host (`sudo apt install nginx`)
- Certbot for SSL (`sudo apt install certbot python3-certbot-nginx`)
- 2GB RAM minimum
- 5GB disk space

### Domain Setup
- Domain name pointed to VPS IP (A record)
- Example: `dhamma.yourdomain.com`

## Deployment Steps

### 1. Prepare Environment

```bash
# Clone repository
cd /opt
sudo git clone https://github.com/natbkgift/dhamma-channel-automation.git
cd dhamma-channel-automation

# Create .env file
sudo cp .env.example .env
sudo nano .env
```

### 2. Configure Environment Variables

Edit `/opt/dhamma-channel-automation/.env`:

```bash
# FlowBiz Standard Variables
APP_SERVICE_NAME="dhamma-automation"
APP_ENV="production"
APP_LOG_LEVEL="INFO"
APP_CORS_ORIGINS='["https://dhamma.yourdomain.com"]'
FLOWBIZ_VERSION="1.0.0"
FLOWBIZ_BUILD_SHA="abc123def"

# Security (CHANGE THESE!)
SECRET_KEY="your-secure-random-key-here"
ADMIN_USERNAME="your-admin-username"
ADMIN_PASSWORD="your-secure-password"

# Application
OUTPUT_DIR="/app/output"
DATA_DIR="/app/data"
```

### 3. Build and Start Service

```bash
# Load allocated port
source config/flowbiz_port.env

# Build Docker image
sudo docker-compose --env-file config/flowbiz_port.env build

# Start service (binds to 127.0.0.1:${FLOWBIZ_ALLOCATED_PORT})
sudo docker-compose --env-file config/flowbiz_port.env up -d

# Verify service is running
sudo docker ps | grep dhamma-web
curl "http://127.0.0.1:${FLOWBIZ_ALLOCATED_PORT}/healthz"
```

Expected output:
```json
{"status":"ok","service":"dhamma-automation","version":"1.0.0"}
```

### 4. Configure System Nginx

Copy the nginx configuration template:

```bash
# Copy template to nginx sites-available
sudo cp nginx/dhamma-automation.conf /etc/nginx/sites-available/dhamma-automation.conf

# Edit with your domain
sudo nano /etc/nginx/sites-available/dhamma-automation.conf
```

Enable the site:

```bash
# Create symlink
sudo ln -s /etc/nginx/sites-available/dhamma-automation.conf /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

### 5. Setup SSL with Let's Encrypt

```bash
# Obtain SSL certificate
sudo certbot --nginx -d dhamma.yourdomain.com

# Test automatic renewal
sudo certbot renew --dry-run
```

Certbot will automatically update the nginx config with SSL settings.

### 6. Verify Deployment

```bash
# Test health endpoint
curl https://dhamma.yourdomain.com/healthz

# Test metadata endpoint
curl https://dhamma.yourdomain.com/v1/meta

# Check logs
sudo docker logs dhamma-web --tail 50
```

### Quick runtime verification

Run the automated runtime check (reads the port from `config/flowbiz_port.env`):

```bash
bash scripts/runtime_verify.sh
```

## Port Binding Verification

Verify ONLY localhost binding:

```bash
# Check docker port binding
sudo docker ps --format "table {{.Names}}\t{{.Ports}}" | grep dhamma

# Expected: 127.0.0.1:${FLOWBIZ_ALLOCATED_PORT}->8000/tcp
# NOT: 0.0.0.0:${FLOWBIZ_ALLOCATED_PORT}->8000/tcp

# Check with netstat
source config/flowbiz_port.env
sudo netstat -tulpn | grep "${FLOWBIZ_ALLOCATED_PORT}"

# Expected: 127.0.0.1:${FLOWBIZ_ALLOCATED_PORT} (NOT 0.0.0.0:${FLOWBIZ_ALLOCATED_PORT})
```

## Maintenance

### Viewing Logs

```bash
# Service logs
sudo docker logs dhamma-web -f

# Nginx access logs
sudo tail -f /var/log/nginx/access.log

# Nginx error logs
sudo tail -f /var/log/nginx/error.log
```

### Updating Service

```bash
cd /opt/dhamma-channel-automation

# Pull latest changes
sudo git pull

# Rebuild and restart
sudo docker-compose --env-file config/flowbiz_port.env down
sudo docker-compose --env-file config/flowbiz_port.env build
sudo docker-compose --env-file config/flowbiz_port.env up -d

# Verify health
source config/flowbiz_port.env
curl "http://127.0.0.1:${FLOWBIZ_ALLOCATED_PORT}/healthz"
```

### Restart Service

```bash
# Restart container
sudo docker-compose --env-file config/flowbiz_port.env restart

# Or full restart
sudo docker-compose --env-file config/flowbiz_port.env down
sudo docker-compose --env-file config/flowbiz_port.env up -d
```

### Reload Nginx

```bash
# Test config
sudo nginx -t

# Reload
sudo systemctl reload nginx

# Or restart
sudo systemctl restart nginx
```

## Monitoring

### Health Checks

Setup automated health checks (e.g., cron job, monitoring service):

```bash
# Health check script
#!/bin/bash
source /opt/dhamma-channel-automation/config/flowbiz_port.env
STATUS=$(curl -s "http://127.0.0.1:${FLOWBIZ_ALLOCATED_PORT}/healthz" | jq -r .status)
if [ "$STATUS" != "ok" ]; then
    echo "Service unhealthy!"
    # Send alert
fi
```

### Key Metrics

Monitor these endpoints:
- `/healthz` - Service health (should return 200)
- `/v1/meta` - Service metadata and version

## Troubleshooting

### Service Won't Start

```bash
# Check logs
sudo docker logs dhamma-web

# Check port availability
source config/flowbiz_port.env
sudo lsof -i :"${FLOWBIZ_ALLOCATED_PORT}"

# Verify environment variables
sudo docker exec dhamma-web env | grep -E "APP_|FLOWBIZ_"
```

### Port Binding Issues

```bash
# Check if port is already in use
source config/flowbiz_port.env
sudo lsof -i :"${FLOWBIZ_ALLOCATED_PORT}"

# Check docker port binding
sudo docker ps | grep dhamma

# If bound to 0.0.0.0, fix docker-compose.yml:
# ports:
#   - "127.0.0.1:${FLOWBIZ_ALLOCATED_PORT}:8000"  # Correct
#   - "${FLOWBIZ_ALLOCATED_PORT}:8000"            # Wrong!
```

### Nginx Errors

```bash
# Check nginx config syntax
sudo nginx -t

# Check nginx status
sudo systemctl status nginx

# View nginx error logs
sudo tail -50 /var/log/nginx/error.log
```

### SSL Certificate Issues

```bash
# Check certificate status
sudo certbot certificates

# Renew certificate
sudo certbot renew

# Test renewal
sudo certbot renew --dry-run
```

## Security Checklist

Before going to production:

- [ ] Changed `SECRET_KEY` in `.env`
- [ ] Changed `ADMIN_USERNAME` and `ADMIN_PASSWORD`
- [ ] Service binds to `127.0.0.1:${FLOWBIZ_ALLOCATED_PORT}` (NOT `0.0.0.0`)
- [ ] System Nginx configured with SSL
- [ ] Firewall rules configured (only 80, 443 open)
- [ ] Docker containers run as non-root user (if applicable)
- [ ] Regular backup schedule configured
- [ ] Monitoring and alerting configured

## Backup and Recovery

### Backup Data

```bash
# Backup output and data directories
sudo tar -czf dhamma-backup-$(date +%Y%m%d).tar.gz \
  /opt/dhamma-channel-automation/output \
  /opt/dhamma-channel-automation/data \
  /opt/dhamma-channel-automation/.env

# Upload to secure storage
```

### Recovery

```bash
# Extract backup
sudo tar -xzf dhamma-backup-YYYYMMDD.tar.gz -C /opt/dhamma-channel-automation/

# Restart service
cd /opt/dhamma-channel-automation
sudo docker-compose --env-file config/flowbiz_port.env restart
```

## References

- [Project Contract](./PROJECT_CONTRACT.md) - FlowBiz integration contract
- [Guardrails](./GUARDRAILS.md) - Automated compliance checks
- [FlowBiz VPS Status](https://github.com/natbkgift/flowbiz-ai-core/blob/main/docs/VPS_STATUS.md)
- [System Nginx ADR](https://github.com/natbkgift/flowbiz-ai-core/blob/main/docs/ADR_SYSTEM_NGINX.md)
- [System Nginx Operations](https://github.com/natbkgift/flowbiz-ai-core/blob/main/docs/CODEX_SYSTEM_NGINX_FIRST.md)
