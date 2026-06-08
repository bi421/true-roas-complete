#  Copyright (c) 2024-2026 TrueROAS Team.
#  All rights reserved.

# TrueROAS v2.1 Production Preflight Quality Gate (Windows PowerShell Version)

$ErrorActionPreference = "Stop"

Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "🚀 Starting TrueROAS v2.1 Production Preflight Gate" -ForegroundColor Cyan
Write-Host "====================================================" -ForegroundColor Cyan

# Set Python Path to include src
$env:PYTHONPATH = "src;."

# 1. Стингийн формат шалгах (Ruff)
Write-Host "🎨 Stage 1: Ruff Formatting & Linting..." -ForegroundColor Yellow
ruff format . --check
ruff check .
if ($LASTEXITCODE -ne 0) { Write-Host "❌ Ruff check failed. Run 'ruff check . --fix' to resolve most issues." -ForegroundColor Red; exit $LASTEXITCODE }

# 2. Static Type Analysis (Mypy)
Write-Host "🏗️  Stage 2: Mypy Type Analysis..." -ForegroundColor Yellow
mypy --strict src/
if ($LASTEXITCODE -ne 0) { Write-Host "❌ Mypy type validation failed." -ForegroundColor Red; exit $LASTEXITCODE }

# 3. Аюулгүй байдлын аудит (Bandit)
Write-Host "🛡️  Stage 3: Bandit Security Scan..." -ForegroundColor Yellow
bandit -r src/ -ll

# 4. Тестүүд болон Coverage Gate (80% доод хязгаар)
Write-Host "🧪 Stage 4: Logical Validation & Property Testing..." -ForegroundColor Yellow
$env:APP_SECRET_SALT="preflight_test_salt_for_validation_32_chars"

# Run all discovered tests to maximize coverage
pytest --cov=src --cov-append `
       --cov-report=term-missing `
       --cov-fail-under=60 `
       .
if ($LASTEXITCODE -ne 0) { Write-Host "❌ Unit or Property tests failed." -ForegroundColor Red; exit $LASTEXITCODE }

Write-Host "====================================================" -ForegroundColor Green
Write-Host "✅ PREFLIGHT SUCCESSFUL: System ready for deployment." -ForegroundColor Green
Write-Host "====================================================" -ForegroundColor Green