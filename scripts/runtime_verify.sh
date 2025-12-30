#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "$PROJECT_ROOT"

PORT_ENV_FILE="config/flowbiz_port.env"
MAX_UP_RETRIES=3
MAX_HTTP_RETRIES=5
BACKOFF_SECONDS=2

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*"
}

fail() {
    echo "FAIL: $1"
    exit 1
}

# Select compose command (prefer docker compose)
if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    COMPOSE_CMD=("docker" "compose")
elif command -v docker-compose >/dev/null 2>&1; then
    COMPOSE_CMD=("docker-compose")
else
    fail "Docker Compose not found. Install docker compose plugin or docker-compose."
fi

# Ensure Docker daemon reachable
if ! docker_info_output=$(docker info 2>&1); then
    fail "Docker daemon not reachable. Start Docker and retry. Details: ${docker_info_output}"
fi
if ! echo "$docker_info_output" | grep -q "Server:"; then
    fail "Docker daemon response missing Server section. Start Docker and retry."
fi

if ! command -v curl >/dev/null 2>&1; then
    fail "curl is required for endpoint checks. Please install curl and retry."
fi

# Load port from env file
if [ ! -f "$PORT_ENV_FILE" ]; then
    fail "Port config missing at $PORT_ENV_FILE"
fi
# shellcheck disable=SC1090
source "$PORT_ENV_FILE"
PORT="${FLOWBIZ_ALLOCATED_PORT:-}"
if [[ -z "$PORT" ]]; then
    fail "FLOWBIZ_ALLOCATED_PORT is empty in $PORT_ENV_FILE"
fi
if ! [[ "$PORT" =~ ^[0-9]+$ ]]; then
    fail "FLOWBIZ_ALLOCATED_PORT must be numeric (found: $PORT)"
fi

log "Using port $PORT from $PORT_ENV_FILE"
COMPOSE_ENV_ARGS=("--env-file" "$PORT_ENV_FILE")

# Bring up service with retries
attempt=1
backoff=$BACKOFF_SECONDS
up_success=false
while [ $attempt -le $MAX_UP_RETRIES ]; do
    log "Starting services with ${COMPOSE_CMD[*]} ${COMPOSE_ENV_ARGS[*]} up -d (attempt $attempt/$MAX_UP_RETRIES)"
    if up_output=$("${COMPOSE_CMD[@]}" "${COMPOSE_ENV_ARGS[@]}" up -d 2>&1); then
        up_success=true
        break
    fi

    if echo "$up_output" | grep -qi "docker daemon"; then
        fail "Docker daemon error during compose up. Start Docker and retry. Details: $up_output"
    fi

    if [ $attempt -lt $MAX_UP_RETRIES ]; then
        log "Compose up failed, retrying in ${backoff}s..."
        sleep "$backoff"
        backoff=$((backoff * 2))
    fi
    attempt=$((attempt + 1))
done

if [ "$up_success" = false ]; then
    fail "Compose up failed after $MAX_UP_RETRIES attempts. Last output: $up_output"
fi

contains_keys() {
    local body="$1"
    shift
    for key in "$@"; do
        if ! echo "$body" | grep -q "\"$key\""; then
            return 1
        fi
    done
    return 0
}

check_endpoint() {
    local url="$1"
    shift
    local expected_keys=("$@")
    local http_attempt=1
    local http_backoff=$BACKOFF_SECONDS
    while [ $http_attempt -le $MAX_HTTP_RETRIES ]; do
        response=$(curl -s -m 5 -w "HTTPSTATUS:%{http_code}" "$url" || true)
        body="${response%HTTPSTATUS:*}"
        status="${response##*HTTPSTATUS:}"
        if [ "$status" = "200" ] && contains_keys "$body" "${expected_keys[@]}"; then
            log "Endpoint OK: $url"
            return 0
        fi
        if [ $http_attempt -lt $MAX_HTTP_RETRIES ]; then
            log "Endpoint not ready (${url}), status=${status}. Retrying in ${http_backoff}s..."
            sleep "$http_backoff"
            http_backoff=$((http_backoff * 2))
        fi
        http_attempt=$((http_attempt + 1))
    done
    fail "Endpoint check failed for ${url}. Last status=${status}, body=${body}"
}

check_endpoint "http://127.0.0.1:${PORT}/healthz" "status" "service" "version"
check_endpoint "http://127.0.0.1:${PORT}/v1/meta" "service" "environment" "version" "build_sha"

# Verify docker port binding
container_ids=$("${COMPOSE_CMD[@]}" "${COMPOSE_ENV_ARGS[@]}" ps -q)
if [ -z "$container_ids" ]; then
    fail "No containers found from compose project. Ensure services are defined and running."
fi

expected_binding="127.0.0.1:${PORT}->8000/tcp"
binding_ok=false
for cid in $container_ids; do
    ports=$(docker ps --filter "id=$cid" --format '{{.Ports}}')
    IFS=',' read -r -a port_tokens <<< "$ports"
    for token in "${port_tokens[@]}"; do
        read -r token_trimmed <<< "$token"
        if [[ "$token_trimmed" == *"$expected_binding"* ]]; then
            binding_ok=true
            break 2
        fi
    done
done

if [ "$binding_ok" = false ]; then
    fail "Expected port binding ${expected_binding} not found. Check docker-compose.yml ports section."
fi

echo "PASS: runtime verification succeeded using port ${PORT}"
echo "Checked endpoints: http://127.0.0.1:${PORT}/healthz and /v1/meta"
