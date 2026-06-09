# TrueROAS v2.1 Production Preflight Quality Gate (PowerShell Version)
# This script performs the final quality checks before deploying the system to LIVE.

$ErrorActionPreference = "Stop"

Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "🚀 Starting TrueROAS v2.1 Production Preflight Gate" -ForegroundColor Cyan
Write-Host "====================================================" -ForegroundColor Cyan

# 1. Check string formatting (Ruff)
Write-Host "🎨 Stage 1: Ruff Formatting & Linting..." -ForegroundColor Yellow
ruff format .
ruff check . --fix

# 2. Static Type Analysis (Mypy)
Write-Host "🏗️  Stage 2: Mypy Type Analysis..." -ForegroundColor Yellow
mypy --strict src/

# 3. Security Audit (Bandit)
Write-Host "🛡️  Stage 3: Bandit Security Scan..." -ForegroundColor Yellow
bandit -r src/ -ll

# 4. Logical Validation & Property Testing
Write-Host "🧪 Stage 4: Logical Validation & Property Testing..." -ForegroundColor Yellow
$env:APP_SECRET_SALT="preflight_test_salt_for_validation_32_chars"
pytest --cov=src --cov-append --cov-report=term-missing --cov-fail-under=60 .
if ($LASTEXITCODE -ne 0) { 
    Write-Host "❌ Pytest failed with exit code $LASTEXITCODE" -ForegroundColor Red
    exit $LASTEXITCODE 
}

Write-Host "====================================================" -ForegroundColor Green
Write-Host "✅ PREFLIGHT SUCCESSFUL: System ready for deployment." -ForegroundColor Green
Write-Host "====================================================" -ForegroundColor Green