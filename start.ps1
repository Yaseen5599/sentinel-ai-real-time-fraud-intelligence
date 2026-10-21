# ==============================================================================
# Sentinel AI — Windows PowerShell Startup Script
# ==============================================================================

$ErrorActionPreference = "Stop"

Write-Host "=== Starting Sentinel AI Fraud Intelligence Platform ===" -ForegroundColor Cyan

# 1. Verify Docker is running
try {
    docker info > $null 2>&1
} catch {
    Write-Host "Docker Desktop does not appear to be running. Please launch Docker Desktop and try again." -ForegroundColor Red
    exit 1
}

# 2. Check for .env file
if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Write-Host "Creating .env from .env.example..." -ForegroundColor Yellow
        Copy-Item ".env.example" ".env"
    }
}

# 3. Launch Docker Compose services
Write-Host "Launching Docker containers..." -ForegroundColor Green
docker compose -f docker-compose.prod.yml up -d

# 4. Wait for web frontend and open browser
Write-Host "Waiting for web interface to be ready (http://localhost:3000)..." -ForegroundColor Yellow
$ready = $false
$retries = 30

while (-not $ready -and $retries -gt 0) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:3000" -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            $ready = $true
        }
    } catch {
        Start-Sleep -Seconds 2
        $retries--
    }
}

Write-Host "Sentinel AI is ready!" -ForegroundColor Green
Write-Host "Dashboard: http://localhost:3000" -ForegroundColor Cyan
Write-Host "API Docs:  http://localhost:8000/docs" -ForegroundColor Cyan

# Open default browser
Start-Process "http://localhost:3000"
