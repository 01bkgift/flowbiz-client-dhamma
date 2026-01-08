#!/bin/bash
set -euo pipefail

# Mandatory checks
if [ -z "${VPS_HOST:-}" ] || [ -z "${VPS_PORT:-}" ] || [ -z "${VPS_USER:-}" ] || [ -z "${VPS_SSH_KEY:-}" ]; then
    echo "ERROR: Missing required secrets."
    exit 1
fi

if [ -z "${ROLLBACK_SHA:-}" ]; then
    echo "ERROR: ROLLBACK_SHA is required for rollback action."
    exit 1
fi

REPORT_FILE="deploy_report.json"
STARTED_AT=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

echo "--- ROLLBACK INITIALIZED ---"
echo "Rollback Target SHA: $ROLLBACK_SHA"

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
ssh-keyscan -p "$VPS_PORT" "$VPS_HOST" > known_hosts 2>/dev/null
ssh-keygen -l -f known_hosts

# SSH Base Command
SSH_OPTS="-o ConnectTimeout=30 -o StrictHostKeyChecking=yes -o UserKnownHostsFile=known_hosts -p $VPS_PORT -i $KEY_FILE"

echo "Executing remote rollback steps..."
ssh $SSH_OPTS "$VPS_USER@$VPS_HOST" << EOF
    set -euo pipefail
    cd /opt/dhamma-channel-automation
    
    echo "Verifying Rollback SHA: $ROLLBACK_SHA"
    if ! git cat-file -e "$ROLLBACK_SHA"; then
        echo "ERROR: Rollback SHA $ROLLBACK_SHA not found in VPS repository."
        exit 1
    fi
    
    echo "Resetting to SHA: $ROLLBACK_SHA"
    git reset --hard "$ROLLBACK_SHA"
    
    echo "Running runtime verification..."
    if [ -f scripts/runtime_verify.sh ]; then
        bash scripts/runtime_verify.sh
    fi
    
    echo "Restarting services..."
    docker compose --env-file config/flowbiz_port.env up -d --remove-orphans
    
    echo "Waiting for health check (max 30s)..."
    PORT=\$(grep '^FLOWBIZ_ALLOCATED_PORT=' config/flowbiz_port.env | cut -d'=' -f2)
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
EOF

FINISHED_AT=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Generate Report
cat <<EOF > "$REPORT_FILE"
{
  "status": "success",
  "action": "rollback",
  "target_sha": "$ROLLBACK_SHA",
  "deployed_sha": "$ROLLBACK_SHA",
  "actor": "$GITHUB_ACTOR",
  "started_at": "$STARTED_AT",
  "finished_at": "$FINISHED_AT",
  "vps_host": "$VPS_HOST"
}
EOF

echo "--- ROLLBACK COMPLETE ---"
