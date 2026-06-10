@echo off
set /p EMAIL="Enter your email: "
set /p STORE="Enter Shopify store ID: "
where cargo >nul 2>&1
if %errorlevel% neq 0 (
    winget install Rustlang.Rustup
)
rustup target add wasm32-wasi
set USER_EMAIL=%EMAIL%
set SHOPIFY_STORE_ID=%STORE%
cargo build --release --target wasm32-wasi
echo Build complete: target\wasm32-wasi\release\trueroas.wasm
pause