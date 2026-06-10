#!/bin/bash
set -e

echo "🛡️ TrueROAS One-Click Build"
echo "==========================="

# Check for config.yaml
if [ -f config.yaml ]; then
    echo "[i] Reading configuration from config.yaml..."
    EMAIL=$(grep "^email:" config.yaml | cut -d ':' -f 2 | xargs)
    STORE=$(grep "^shopify_store:" config.yaml | cut -d ':' -f 2 | xargs)
fi

[ -z "$EMAIL" ] && read -p "Enter your business email: " EMAIL
[ -z "$STORE" ] && read -p "Enter Shopify store ID: " STORE

# Check for Rust
if ! command -v cargo &> /dev/null; then
    echo "[!] Rust is missing. Installing..."
    curl --proto '=https' -sSf https://sh.rustup.rs | sh -s -- -y
    source "$HOME/.cargo/env"
fi

# Ensure WASM target
rustup target add wasm32-wasi &> /dev/null

# Set environment
export USER_EMAIL=$EMAIL
export SHOPIFY_STORE_ID=$STORE

echo "[i] Building your personalized binary..."
cargo build --release --target wasm32-wasi

if [ $? -eq 0 ]; then
    echo -e "\n✓ Your personal trueroas.wasm is ready"
    echo "Location: target/wasm32-wasi/release/trueroas.wasm"
else
    echo -e "\n❌ Build failed."
    exit 1
fi

# Make script executable (self-correction)
chmod +x "$0"