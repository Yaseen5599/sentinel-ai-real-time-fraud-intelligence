#!/usr/bin/env bash
# ==============================================================================
# Sentinel AI — System Startup Script
# Starts the Supabase IPv6 bridge, Docker services, and opens the dashboard
# ==============================================================================

set -e
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo "=== Starting Sentinel AI Fraud Intelligence Platform ==="

# 1. Verify Docker is running
if ! docker info >/dev/null 2>&1; then
    echo "Starting Docker Desktop..."
    open -a Docker
    echo "Waiting for Docker daemon to become ready..."
    while ! docker info >/dev/null 2>&1; do
        sleep 2
    done
fi

# 2. Start the Supabase IPv6-to-IPv4 bridge if not already running
if ! lsof -i :6543 >/dev/null 2>&1; then
    echo "Starting Supabase database bridge in background..."
    nohup python3 "$PROJECT_DIR/scripts/supabase_bridge.py" >/dev/null 2>&1 &
    sleep 1
else
    echo "Supabase database bridge is already running on port 6543."
fi

# 3. Launch Docker Compose services
echo "Launching Docker containers..."
docker compose -f docker-compose.prod.yml up -d

# 4. Wait for web frontend and open browser
echo "Waiting for web interface to be ready..."
until curl -s -f http://localhost:3000 >/dev/null 2>&1; do
    sleep 2
done

echo "Sentinel AI is ready!"
echo "Dashboard: http://localhost:3000"
echo "API Docs:  http://localhost:8000/docs"
open http://localhost:3000
