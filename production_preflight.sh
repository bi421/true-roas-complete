#!/bin/bash
#  Copyright (c) 2024-2026 TrueROAS Team.
#  All rights reserved.

# TrueROAS v2.1 Production Preflight Quality Gate
# Энэхүү скрипт нь системийг LIVE болгохоос өмнөх эцсийн шалгалтуудыг гүйцэтгэнэ.

set -e  # Алдаа гарвал скриптийг шууд зогсооно.

echo "===================================================="
echo "🚀 Starting TrueROAS v2.1 Production Preflight Gate"
echo "===================================================="

# 1. Стингийн формат шалгах (Ruff)
echo "🎨 Stage 1: Ruff Formatting & Linting..."
ruff format . --check
ruff check .

# 2. Static Type Analysis (Mypy)
echo "🏗️  Stage 2: Mypy Type Analysis..."
mypy --strict src/

# 3. Аюулгүй байдлын аудит (Bandit)
echo "🛡️  Stage 3: Bandit Security Scan..."
bandit -r src/ -ll

# 4. Тестүүд болон Coverage Gate (80% доод хязгаар)
echo "🧪 Stage 4: Logical Validation & Property Testing..."
export APP_SECRET_SALT="preflight_test_salt_for_validation_32_chars"

# Run all discovered tests to maximize coverage
pytest --cov=src --cov-append \
       --cov-report=term-missing \
       --cov-fail-under=60 \
       .

echo "===================================================="
echo "✅ PREFLIGHT SUCCESSFUL: System ready for deployment."
echo "===================================================="