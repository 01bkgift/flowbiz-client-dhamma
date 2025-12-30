#!/bin/bash
# FlowBiz Guardrails Check
# Automated compliance verification for FlowBiz Client Product standards

echo "==================================================================="
echo "  FlowBiz Guardrails Check"
echo "==================================================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASS_COUNT=0
WARN_COUNT=0
FAIL_COUNT=0

check_pass() {
    echo -e "${GREEN}✓ PASS${NC}: $1"
    PASS_COUNT=$((PASS_COUNT + 1))
}

check_warn() {
    echo -e "${YELLOW}⚠ WARN${NC}: $1"
    WARN_COUNT=$((WARN_COUNT + 1))
}

check_fail() {
    echo -e "${RED}✗ FAIL${NC}: $1"
    FAIL_COUNT=$((FAIL_COUNT + 1))
}

DEFAULT_PORT=3007
PORT_ENV_FILE="config/flowbiz_port.env"
PORT="$DEFAULT_PORT"
if [ -f "$PORT_ENV_FILE" ]; then
    # shellcheck disable=SC1090
    source "$PORT_ENV_FILE"
    if [[ "${FLOWBIZ_ALLOCATED_PORT:-}" =~ ^[0-9]+$ ]]; then
        PORT="$FLOWBIZ_ALLOCATED_PORT"
    else
        check_warn "Invalid FLOWBIZ_ALLOCATED_PORT in $PORT_ENV_FILE - using default $DEFAULT_PORT"
    fi
else
    check_warn "Port config not found at $PORT_ENV_FILE - using default $DEFAULT_PORT"
fi

echo "1. Checking port binding configuration..."
echo "-------------------------------------------------------------------"

# Check docker-compose.yml for localhost binding
if [ -f "docker-compose.yml" ]; then
    if grep -q "127.0.0.1:.*:8000" docker-compose.yml; then
        check_pass "Port binding uses localhost (127.0.0.1)"
    elif grep -q "0.0.0.0:.*:8000" docker-compose.yml; then
        check_fail "Port binding exposes to all interfaces (0.0.0.0) - SECURITY RISK"
    elif grep -qE "^\s+-\s+\"[0-9]+:8000\"" docker-compose.yml; then
        check_fail "Port binding missing localhost specification - defaults to 0.0.0.0"
    else
        check_warn "Could not verify port binding format"
    fi
    
    # Check allocated port variable usage
    # Accept both:
    # - ${FLOWBIZ_ALLOCATED_PORT}
    # - ${FLOWBIZ_ALLOCATED_PORT:?message}
    if grep -qE '127\.0\.0\.1:\$\{FLOWBIZ_ALLOCATED_PORT(:\?[^}]+)?\}:8000' docker-compose.yml; then
        check_pass "Using FLOWBIZ_ALLOCATED_PORT variable (currently ${PORT})"
    elif grep -q "127.0.0.1:${PORT}:8000" docker-compose.yml; then
        check_warn "Using hardcoded port ${PORT} instead of \${FLOWBIZ_ALLOCATED_PORT} variable"
    else
        check_warn "Could not verify allocated port usage"
    fi
else
    check_warn "docker-compose.yml not found - cannot verify port binding"
fi

echo ""
echo "2. Checking environment variables documentation..."
echo "-------------------------------------------------------------------"

if [ -f ".env.example" ]; then
    required_vars=("APP_SERVICE_NAME" "APP_ENV" "APP_LOG_LEVEL" "APP_CORS_ORIGINS" "FLOWBIZ_VERSION" "FLOWBIZ_BUILD_SHA")
    for var in "${required_vars[@]}"; do
        if grep -q "^${var}=" .env.example; then
            check_pass "Required env var ${var} documented"
        else
            check_fail "Required env var ${var} missing from .env.example"
        fi
    done
else
    check_fail ".env.example file not found"
fi

echo ""
echo "3. Checking required documentation..."
echo "-------------------------------------------------------------------"

required_docs=("docs/PROJECT_CONTRACT.md" "docs/DEPLOYMENT.md" "docs/GUARDRAILS.md" "docs/CODEX_PREFLIGHT.md")
for doc in "${required_docs[@]}"; do
    if [ -f "$doc" ]; then
        check_pass "Documentation exists: $doc"
    else
        check_fail "Missing required documentation: $doc"
    fi
done

echo ""
echo "4. Checking nginx configuration..."
echo "-------------------------------------------------------------------"

if [ -f "nginx/dhamma-automation.conf" ]; then
    check_pass "Nginx config template exists"
    
    # Check for deployment note about FLOWBIZ_ALLOCATED_PORT
    if grep -q "FLOWBIZ_ALLOCATED_PORT from config/flowbiz_port.env" nginx/dhamma-automation.conf; then
        check_pass "Nginx config has deployment note for FLOWBIZ_ALLOCATED_PORT"
    else
        check_warn "Nginx config missing deployment note for FLOWBIZ_ALLOCATED_PORT"
    fi
else
    check_fail "Nginx config template missing: nginx/dhamma-automation.conf"
fi

echo ""
echo "5. Checking Dockerfile security..."
echo "-------------------------------------------------------------------"

if [ -f "Dockerfile" ]; then
    # Check if running as root (USER directive should exist)
    if grep -q "^USER " Dockerfile; then
        check_pass "Dockerfile uses non-root user"
    else
        check_warn "Dockerfile may run as root (no USER directive found)"
    fi
    
    # Check for exposed secrets
    if grep -iE "password|secret|key|token" Dockerfile | grep -qv "^#"; then
        check_warn "Dockerfile may contain hardcoded secrets - review manually"
    else
        check_pass "No obvious hardcoded secrets in Dockerfile"
    fi
else
    check_warn "Dockerfile not found"
fi

echo ""
echo "6. Checking contract endpoints (if service is running)..."
echo "-------------------------------------------------------------------"

# Check if service is running on localhost:3007
SERVICE_RUNNING=false
if command -v curl &> /dev/null; then
    if curl -s -f -m 2 "http://127.0.0.1:${PORT}/healthz" > /dev/null 2>&1; then
        SERVICE_RUNNING=true
    fi
fi

if [ "$SERVICE_RUNNING" = true ]; then
    # Test /healthz endpoint
    healthz_response=$(curl -s -f "http://127.0.0.1:${PORT}/healthz" 2>/dev/null || echo "")
    if [ -n "$healthz_response" ]; then
        if echo "$healthz_response" | grep -q '"status"' && \
           echo "$healthz_response" | grep -q '"service"' && \
           echo "$healthz_response" | grep -q '"version"'; then
            check_pass "/healthz endpoint responds with correct schema"
        else
            check_fail "/healthz endpoint schema incorrect"
        fi
    else
        check_fail "/healthz endpoint not responding"
    fi
    
    # Test /v1/meta endpoint
    meta_response=$(curl -s -f "http://127.0.0.1:${PORT}/v1/meta" 2>/dev/null || echo "")
    if [ -n "$meta_response" ]; then
        if echo "$meta_response" | grep -q '"service"' && \
           echo "$meta_response" | grep -q '"environment"' && \
           echo "$meta_response" | grep -q '"version"' && \
           echo "$meta_response" | grep -q '"build_sha"'; then
            check_pass "/v1/meta endpoint responds with correct schema"
        else
            check_fail "/v1/meta endpoint schema incorrect"
        fi
    else
        check_fail "/v1/meta endpoint not responding"
    fi
else
    check_warn "Service not running on localhost:${PORT} - skipping endpoint checks"
    echo "         Start service with: docker-compose --env-file config/flowbiz_port.env up -d (or docker compose equivalent)"
fi

echo ""
echo "==================================================================="
echo "  Summary"
echo "==================================================================="
echo -e "${GREEN}Passed${NC}:   $PASS_COUNT"
echo -e "${YELLOW}Warnings${NC}: $WARN_COUNT"
echo -e "${RED}Failed${NC}:   $FAIL_COUNT"
echo ""

if [ $FAIL_COUNT -gt 0 ]; then
    echo -e "${RED}RESULT: FAIL${NC} - $FAIL_COUNT critical issue(s) found"
    echo "Please fix the failures before deployment."
    exit 1
elif [ $WARN_COUNT -gt 0 ]; then
    echo -e "${YELLOW}RESULT: PASS with WARNINGS${NC} - $WARN_COUNT warning(s)"
    echo "Warnings should be reviewed but do not block deployment."
    exit 0
else
    echo -e "${GREEN}RESULT: PASS${NC} - All checks passed!"
    exit 0
fi
