#!/usr/bin/env bash
# ==============================================================================
# Sentinel AI — System Shutdown Script
# ==============================================================================

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo "=== Stopping Sentinel AI Fraud Intelligence Platform ==="

# 1. Stop Docker Compose services
docker compose -f docker-compose.prod.yml down

# 2. Stop Supabase bridge if running
BRIDGE_PID=$(lsof -ti :6543 2>/dev/null || true)
if [ -n "$BRIDGE_PID" ]; then
    echo "Stopping Supabase bridge (PID $BRIDGE_PID)..."
    kill -9 $BRIDGE_PID 2>/dev/null || true
fi

echo "Sentinel AI stopped."
