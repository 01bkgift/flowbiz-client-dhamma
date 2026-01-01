# FlowBiz Client Project Contract

## Service Identity

- **Service Name**: `dhamma-automation`
- **Repository**: `natbkgift/dhamma-channel-automation`
- **Type**: FlowBiz Client Product
- **Port Allocation**: 3007

> **Important**: Service identity comes from `APP_SERVICE_NAME` environment variable, NOT the repository name.

## Required Endpoints

All FlowBiz client projects MUST implement these standardized HTTP endpoints:

### GET /healthz

**Purpose**: Health check for monitoring and load balancing

**Response**: HTTP 200 OK
```json
{
  "status": "ok",
  "service": "<APP_SERVICE_NAME>",
  "version": "<FLOWBIZ_VERSION>"
}
```

**Requirements**:
- MUST return 200 OK when service is operational
- MUST be fast (<50ms)
- MUST NOT touch external services or databases
- MUST NOT require authentication

### GET /v1/meta

**Purpose**: Service metadata for deployment verification and debugging

**Response**: HTTP 200 OK
```json
{
  "service": "<APP_SERVICE_NAME>",
  "environment": "<APP_ENV>",
  "version": "<FLOWBIZ_VERSION>",
  "build_sha": "<FLOWBIZ_BUILD_SHA>"
}
```

**Requirements**:
- MUST return 200 OK
- MUST be fast (<50ms)
- MUST NOT touch external services or databases
- MUST NOT require authentication

## Required Environment Variables

### FlowBiz Standard Variables (Required)

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `APP_SERVICE_NAME` | string | **required** | Service identity (NOT repo name) |
| `APP_ENV` | enum | `dev` | Environment: `dev`, `staging`, or `prod` |
| `APP_LOG_LEVEL` | enum | `INFO` | Log level: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `APP_CORS_ORIGINS` | JSON array | `["*"]` | CORS allowed origins as JSON string |
| `FLOWBIZ_VERSION` | semver | `0.0.0` | Semantic version (set by CI/CD) |
| `FLOWBIZ_BUILD_SHA` | string | `dev` | Git commit SHA (set by CI/CD) |

### Example `.env` Configuration

```bash
# FlowBiz Standard Variables
APP_SERVICE_NAME="dhamma-automation"
APP_ENV="dev"
APP_LOG_LEVEL="INFO"
APP_CORS_ORIGINS='["*"]'
FLOWBIZ_VERSION="0.0.0"
FLOWBIZ_BUILD_SHA="dev"
```

## Port Binding Rules

### Development
- Internal Port: `8000` (FastAPI default)
- External Port: `3007` (FlowBiz allocated)
- Binding: `127.0.0.1:3007:8000` (localhost only)

### Production (Docker)
- Container exposes port `8000` internally
- Host binds to `127.0.0.1:3007` (localhost only)
- System Nginx proxies to `http://127.0.0.1:3007`

**Critical Security Rules**:
- ✅ MUST bind to `127.0.0.1` (localhost) only
- ❌ NEVER bind to `0.0.0.0` (all interfaces)
- ❌ NEVER expose ports directly to the internet
- ✅ System Nginx is the ONLY public-facing reverse proxy

## Content Integrity (Metadata)

- Do not translate/rewrite metadata; preserve as-is when reading, writing, or uploading.

## Runtime Contract

### Startup
1. Service MUST start within 30 seconds
2. Service MUST respond to `/healthz` immediately after startup
3. Service MUST log startup success to stdout

### Shutdown
1. Service MUST handle SIGTERM gracefully
2. Service MUST complete in-flight requests within 30 seconds
3. Service MUST close connections cleanly

### Monitoring
1. Service MUST respond to `/healthz` checks every 30 seconds
2. Service failure MUST return non-200 status or timeout
3. Logs MUST be written to stdout/stderr for collection

## Compliance Verification

To verify compliance with this contract:

```bash
# 1. Check endpoints
curl http://localhost:3007/healthz
curl http://localhost:3007/v1/meta

# 2. Verify environment variables
docker exec dhamma-web env | grep -E "APP_|FLOWBIZ_"

# 3. Check port binding
docker ps | grep dhamma-web
# Should show: 127.0.0.1:3007->8000/tcp

# 4. Run automated checks
make guardrails
```

## Non-Breaking Migration

This contract was added to an existing project. Compatibility measures:

1. **Legacy Environment Variables**: Old `APP_NAME` still works, maps to `APP_SERVICE_NAME`
2. **Existing Endpoints**: All original endpoints remain unchanged
3. **Authentication**: New contract endpoints do NOT require auth
4. **Backwards Compatibility**: All existing functionality preserved

## References

- [Deployment Guide](./DEPLOYMENT.md) - Production deployment instructions
- [Guardrails](./GUARDRAILS.md) - Automated compliance checks
- [FlowBiz VPS Status](https://github.com/natbkgift/flowbiz-ai-core/blob/main/docs/VPS_STATUS.md) - Port allocation registry
- [System Nginx ADR](https://github.com/natbkgift/flowbiz-ai-core/blob/main/docs/ADR_SYSTEM_NGINX.md) - Reverse proxy architecture
