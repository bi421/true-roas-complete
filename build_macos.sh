#!/bin/bash
read -p "Email: " EMAIL
read -p "Shopify Store: " STORE
export USER_EMAIL=$EMAIL
export SHOPIFY_STORE_ID=$STORE
if ! command -v cargo &> /dev/null; then
    curl --proto '=https' -sSf https://sh.rustup.rs | sh -s -- -y
    source $HOME/.cargo/env
fi
rustup target add wasm32-wasi
cargo build --release --target wasm32-wasi
echo "✓ Done: target/wasm32-wasi/release/trueroas.wasm"