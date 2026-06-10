#!/bin/bash
#  Copyright (c) 2024-2026 TrueROAS Team.
#  All rights reserved.

# TrueROAS v2.1 Production Preflight Quality Gate
# This script performs the final quality checks before deploying the system to LIVE.

set -e  # Exit immediately if a command exits with a non-zero status.

echo "===================================================="
echo "🚀 Starting TrueROAS v2.1 Production Preflight Gate"
echo "===================================================="

# 1. Check string formatting (Ruff)
echo "🎨 Stage 1: Ruff Formatting & Linting..."
ruff format . --check
ruff check .

# 2. Static Type Analysis (Mypy)
echo "🏗️  Stage 2: Mypy Type Analysis..."
mypy --strict src/

# 3. Security Audit (Bandit)
echo "🛡️  Stage 3: Bandit Security Scan..."
bandit -r src/ -ll

# 4. Logical Validation & Property Testing
echo "🧪 Stage 4: Logical Validation & Property Testing..."

# ШАЛГАЛТ: APP_SECRET_SALT тохируулагдсан эсэх болон аюулгүй байдлыг хангах
if [ -z "$APP_SECRET_SALT" ]; then
  echo "🚨 АЛДАА: APP_SECRET_SALT орчны хувьсагч тохируулагдаагүй байна."
  exit 1
fi

if [ ${#APP_SECRET_SALT} -lt 32 ]; then
  echo "🚨 АЛДАА: APP_SECRET_SALT хэтэрхий богино байна (хамгийн багадаа 32 тэмдэгт)."
  exit 1
fi

if [ "$APP_SECRET_SALT" == "preflight_test_salt_for_validation_32_chars" ]; then
  echo "🚨 АЛДАА: Жишээ (placeholder) salt ашиглаж байна. Үйлдвэрлэлд ашиглах нууц үг оруулна уу."
  exit 1
fi

# Run all discovered tests to maximize coverage
pytest --cov=src --cov-append \
       --cov-report=term-missing \
       --cov-fail-under=60 \
       .

echo "===================================================="
echo "✅ PREFLIGHT SUCCESSFUL: System ready for deployment."
echo "===================================================="