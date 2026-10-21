# ==============================================================================
# Sentinel AI — Windows PowerShell Shutdown Script
# ==============================================================================

Write-Host "=== Stopping Sentinel AI Fraud Intelligence Platform ===" -ForegroundColor Cyan

docker compose -f docker-compose.prod.yml down

Write-Host "Sentinel AI stopped." -ForegroundColor Green
