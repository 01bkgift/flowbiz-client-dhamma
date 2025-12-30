# FlowBiz Guardrails

## Overview

Guardrails are automated checks that verify compliance with FlowBiz Client Product standards. These checks are non-blocking but provide early warnings about potential issues.

## Automated Checks

### 1. Port Binding Verification

**Check**: Service binds ONLY to localhost (127.0.0.1)

**Why**: Public port bindings bypass System Nginx and expose services directly to the internet.

**Port source**: `config/flowbiz_port.env` (single source of truth for `FLOWBIZ_ALLOCATED_PORT`)

**Verification**:
```bash
# Check docker-compose.yml
grep -E "ports:" docker-compose.yml -A1

# Expected: 127.0.0.1:PORT:PORT
# Forbidden: 0.0.0.0:PORT:PORT or PORT:PORT
```

**Fix**:
```yaml
# Correct
ports:
  - "127.0.0.1:${FLOWBIZ_ALLOCATED_PORT}:8000"

# Wrong
ports:
  - "0.0.0.0:${FLOWBIZ_ALLOCATED_PORT}:8000"  # Exposes to all interfaces
  - "${FLOWBIZ_ALLOCATED_PORT}:8000"          # Defaults to 0.0.0.0
```

### 2. Required Endpoints

**Check**: Contract endpoints exist and return correct schema

**Endpoints**:
- `GET /healthz`
- `GET /v1/meta`

**Verification**:
```bash
# Start service
docker-compose --env-file config/flowbiz_port.env up -d

# Test healthz
source config/flowbiz_port.env
curl "http://127.0.0.1:${FLOWBIZ_ALLOCATED_PORT}/healthz"
# Expected: {"status":"ok","service":"dhamma-automation","version":"..."}

# Test meta
curl "http://127.0.0.1:${FLOWBIZ_ALLOCATED_PORT}/v1/meta"
# Expected: {"service":"...","environment":"...","version":"...","build_sha":"..."}
```

**Fix**: Implement endpoints as specified in [PROJECT_CONTRACT.md](./PROJECT_CONTRACT.md)

### 3. Environment Variables Documentation

**Check**: Required environment variables are documented in .env.example

**Required Variables**:
- `APP_SERVICE_NAME`
- `APP_ENV`
- `APP_LOG_LEVEL`
- `APP_CORS_ORIGINS`
- `FLOWBIZ_VERSION`
- `FLOWBIZ_BUILD_SHA`

**Verification**:
```bash
# Check .env.example
grep -E "APP_SERVICE_NAME|APP_ENV|APP_LOG_LEVEL|APP_CORS_ORIGINS|FLOWBIZ_VERSION|FLOWBIZ_BUILD_SHA" .env.example
```

**Fix**: Add missing variables to `.env.example`

### 4. Dockerfile Security

**Check**: No insecure practices in Dockerfile

**Common Issues**:
- Running as root user
- Exposed secrets in build args
- Unnecessary privileged mode

**Verification**:
```bash
# Check for USER directive
grep -i "USER" Dockerfile

# Check for exposed secrets
grep -iE "password|secret|key|token" Dockerfile
```

**Fix**: Follow Dockerfile security best practices

### 5. Port Allocation Registry

**Check**: Allocated port is available and registered

**Verification**:
```bash
# Check if port is in use
source config/flowbiz_port.env
sudo lsof -i :"${FLOWBIZ_ALLOCATED_PORT}"
netstat -tulpn | grep "${FLOWBIZ_ALLOCATED_PORT}"

# Check VPS Status registry
# https://github.com/natbkgift/flowbiz-ai-core/blob/main/docs/VPS_STATUS.md
```

**Fix**: If port is in use, select nearest available port in range 3001-3099

## Running Guardrails

### Manual Execution

```bash
# Run all checks
make guardrails

# Or directly
bash scripts/guardrails.sh

# Quick runtime verification (brings services up and checks endpoints/ports)
bash scripts/runtime_verify.sh
```

### CI Execution

Guardrails run automatically on every PR via GitHub Actions.

**Workflow**: `.github/workflows/guardrails.yml`

**Behavior**:
- Runs on every pull request
- Non-blocking (warnings only)
- Results posted as PR comment
- Does NOT fail the build

### Local Pre-commit

Add guardrails to pre-commit hooks:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: guardrails
        name: FlowBiz Guardrails
        entry: bash scripts/guardrails.sh
        language: system
        pass_filenames: false
        always_run: true
```

## Guardrail Script

The guardrails script (`scripts/guardrails.sh`) checks:

1. **Port Binding**: Verify localhost binding in docker-compose.yml
2. **Endpoints**: Test /healthz and /v1/meta responses
3. **Environment**: Check required variables in .env.example
4. **Documentation**: Verify required docs exist
5. **Security**: Check for common security issues

### Example Output

```
=== FlowBiz Guardrails Check ===

✓ Port binding: PASS (127.0.0.1:${FLOWBIZ_ALLOCATED_PORT})
✓ /healthz endpoint: PASS
✓ /v1/meta endpoint: PASS
✓ Environment variables: PASS
✓ Documentation: PASS
✗ Security: WARN (Running as root in container)

Overall: PASS with 1 warning(s)
```

## Interpreting Results

### PASS ✓
- Check passed completely
- No action required

### WARN ⚠
- Check passed but has recommendations
- Action recommended but not required
- Won't block deployment

### FAIL ✗
- Check failed
- Action required before deployment
- May block production deployment

## Common Failures and Fixes

### Port Binding Failure

**Error**: "Port binding exposes service publicly"

**Fix**:
```yaml
# docker-compose.yml
ports:
  - "127.0.0.1:${FLOWBIZ_ALLOCATED_PORT}:8000"  # Add 127.0.0.1
```

### Missing Endpoint

**Error**: "/healthz endpoint returned 404"

**Fix**: Implement missing endpoint in `app/main.py`:
```python
@app.get("/healthz")
async def healthz():
    return {
        "status": "ok",
        "service": config.APP_SERVICE_NAME,
        "version": config.FLOWBIZ_VERSION,
    }
```

### Environment Variables

**Error**: "Required env var APP_SERVICE_NAME not in .env.example"

**Fix**: Add to `.env.example`:
```bash
APP_SERVICE_NAME="dhamma-automation"
```

### Documentation Missing

**Error**: "Required documentation docs/PROJECT_CONTRACT.md not found"

**Fix**: Create missing documentation files

## Exemptions

Some checks can be exempted with justification:

### Exemption File

Create `.guardrails-exemptions.yml`:

```yaml
exemptions:
  - check: port_binding
    reason: "Using custom proxy setup for [specific reason]"
    approved_by: "Technical Lead Name"
    expires: "2024-12-31"
    
  - check: root_user
    reason: "Container requires root for [specific operation]"
    approved_by: "Security Team"
    expires: "2024-06-30"
```

### Exemption Rules

1. **Must have valid business/technical reason**
2. **Must be approved by appropriate authority**
3. **Must have expiration date**
4. **Must be reviewed quarterly**

## Integration with CI/CD

### Pull Request Checks

Guardrails run on every PR:

```yaml
# .github/workflows/guardrails.yml
name: Guardrails

on:
  pull_request:
    branches: [ main ]

jobs:
  guardrails:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run Guardrails
        run: bash scripts/guardrails.sh
        continue-on-error: true  # Non-blocking
```

### Deployment Gates

For production deployments, make guardrails blocking:

```yaml
jobs:
  deploy:
    needs: guardrails  # Require guardrails to pass
    if: success()      # Only deploy if guardrails succeed
```

## Monitoring

### Continuous Monitoring

Even after deployment, periodically verify compliance:

```bash
# Weekly cron job
0 2 * * 1 cd /opt/dhamma-channel-automation && bash scripts/guardrails.sh
```

### Alerts

Configure alerts for guardrail failures:

```bash
# Send alert if guardrails fail
bash scripts/guardrails.sh || send_alert "Guardrails failed"
```

## References

- [Project Contract](./PROJECT_CONTRACT.md) - Compliance requirements
- [Deployment Guide](./DEPLOYMENT.md) - Production setup
- [Codex Preflight](./CODEX_PREFLIGHT.md) - Pre-deployment checklist
- [FlowBiz VPS Status](https://github.com/natbkgift/flowbiz-ai-core/blob/main/docs/VPS_STATUS.md)
- [System Nginx ADR](https://github.com/natbkgift/flowbiz-ai-core/blob/main/docs/ADR_SYSTEM_NGINX.md)

## Support

If guardrails fail and you need help:

1. Check this documentation for common issues
2. Review the specific error message
3. Consult the referenced FlowBiz core docs
4. Ask in team channel with error details
