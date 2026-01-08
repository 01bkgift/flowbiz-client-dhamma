#!/bin/bash
set -euo pipefail

# Mandatory checks
if [ -z "${VPS_HOST:-}" ] || [ -z "${VPS_PORT:-}" ] || [ -z "${VPS_USER:-}" ] || [ -z "${VPS_SSH_KEY:-}" ] || [ -z "${VPS_KNOWN_HOST:-}" ]; then
    echo "ERROR: Missing required secrets (VPS_HOST, VPS_PORT, VPS_USER, VPS_SSH_KEY, VPS_KNOWN_HOST)."
    exit 1
fi

if [ -z "${TARGET_SHA:-}" ]; then
    echo "ERROR: TARGET_SHA is a required input for deterministic deployment."
    exit 1
fi
REPORT_FILE="deploy_report.json"
STARTED_AT=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

echo "--- DEPLOYMENT INITIALIZED ---"
echo "Repo: $GITHUB_REPOSITORY"
echo "Actor: $GITHUB_ACTOR"
echo "Target SHA: $TARGET_SHA"

# SSH Key Setup
KEY_FILE=$(mktemp)
chmod 600 "$KEY_FILE"
echo "$VPS_SSH_KEY" > "$KEY_FILE"

cleanup() {
    rm -f "$KEY_FILE"
    rm -f known_hosts
}
trap cleanup EXIT

# Host Verification
echo "Setting up known hosts..."
if [ -z "${VPS_KNOWN_HOST:-}" ]; then
    echo "ERROR: VPS_KNOWN_HOST is empty."
    exit 1
fi
echo "$VPS_KNOWN_HOST" > known_hosts
echo "Verifying known host key:"
ssh-keygen -l -f known_hosts

# SSH Base Command
SSH_OPTS="-o ConnectTimeout=30 -o StrictHostKeyChecking=yes -o UserKnownHostsFile=known_hosts -p $VPS_PORT -i $KEY_FILE"

echo "Executing remote deployment steps..."
ssh $SSH_OPTS "$VPS_USER@$VPS_HOST" << EOF
    set -euo pipefail
    cd /opt/dhamma-channel-automation
    
    echo "Fetching latest changes..."
    git fetch --all --prune
    
    echo "Checking out SHA: $TARGET_SHA"
    if ! git cat-file -e "$TARGET_SHA"; then
        echo "ERROR: SHA $TARGET_SHA not found on remote."
        exit 1
    fi
    git checkout "$TARGET_SHA"
    git checkout "$TARGET_SHA"

    if [ "${DRY_RUN:-false}" = "true" ]; then
        echo "DRY RUN MODE: Skipping git reset --hard and Docker Compose"
        echo "Validating environment configuration (Dry Run)..."
        if [ ! -f config/flowbiz_port.env ]; then
             echo "WARNING: config/flowbiz_port.env missing (this would fail in production)"
        else
             echo "Config file found."
        fi
        echo "--- DRY RUN COMPLETE ---"
        exit 0
    fi

    git reset --hard "$TARGET_SHA"
    
    echo "Validating environment configuration..."
    if [ ! -f config/flowbiz_port.env ]; then
        echo "ERROR: config/flowbiz_port.env missing."
        exit 1
    fi
    
    # Simple port validation
    PORT=\$(grep '^FLOWBIZ_ALLOCATED_PORT=' config/flowbiz_port.env | cut -d'=' -f2)
    if ! [[ "\$PORT" =~ ^[0-9]+$ ]]; then
        echo "ERROR: Invalid FLOWBIZ_ALLOCATED_PORT: \$PORT"
        exit 1
    fi
    
    echo "Running runtime verification..."
    if [ -f scripts/runtime_verify.sh ]; then
        bash scripts/runtime_verify.sh
    else
        echo "WARNING: scripts/runtime_verify.sh not found, skipping."
    fi
    
    echo "Restarting services with Docker Compose..."
    docker compose --env-file config/flowbiz_port.env up -d --remove-orphans
    
    echo "Waiting for health check (max 30s)..."
    HEALTH_URL="http://127.0.0.1:\$PORT/healthz"
    SUCCESS=0
    for i in {1..15}; do
        if curl -fsS "\$HEALTH_URL" > /dev/null; then
            echo "Health check passed!"
            SUCCESS=1
            break
        fi
        echo "Waiting... (\$i/15)"
        sleep 2
    done
    
    if [ \$SUCCESS -ne 1 ]; then
        echo "ERROR: Health check failed after 30s."
        exit 1
    fi
    
    echo "--- REMOTE DEPLOYMENT SUCCESS ---"
EOF

FINISHED_AT=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Generate Report
cat <<EOF > "$REPORT_FILE"
{
  "status": "success",
  "action": "deploy",
  "target_sha": "$TARGET_SHA",
  "deployed_sha": "$TARGET_SHA",
  "actor": "$GITHUB_ACTOR",
  "started_at": "$STARTED_AT",
  "finished_at": "$FINISHED_AT",
  "vps_host": "$VPS_HOST",
  "dry_run": "${DRY_RUN:-false}"
}
EOF

echo "--- DEPLOYMENT COMPLETE ---"
