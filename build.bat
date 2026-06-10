@echo off
setlocal enabledelayedexpansion

echo 🛡️ TrueROAS One-Click Build
echo ===========================

:: Default values
set EMAIL=
set STORE=

:: Check for config.yaml
if exist config.yaml (
    echo [i] Reading configuration from config.yaml...
    for /f "tokens=2 delims=: " %%a in ('findstr /b "email:" config.yaml') do set EMAIL=%%a
    for /f "tokens=2 delims=: " %%a in ('findstr /b "shopify_store:" config.yaml') do set STORE=%%a
)

if "%EMAIL%"=="" (
    set /p EMAIL="Enter your business email: "
)
if "%STORE%"=="" (
    set /p STORE="Enter Shopify store ID: "
)

:: Check for Rust
where cargo >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Rust is missing. Attempting automatic installation...
    winget install Rustlang.Rustup
    if %errorlevel% neq 0 (
        echo [x] Automatic install failed. Please install Rust manually from https://rustup.rs/
        pause
        exit /b 1
    )
    echo [!] Rust installed. Please restart this terminal and run build.bat again.
    pause
    exit /b 0
)

:: Ensure WASM target
call rustup target add wasm32-wasi >nul 2>&1

:: Set environment for personalization
set USER_EMAIL=%EMAIL%
set SHOPIFY_STORE_ID=%STORE%

echo [i] Building your personalized binary...
cargo build --release --target wasm32-wasi

if %errorlevel% equ 0 (
    echo.
    echo ✓ Your personal trueroas.wasm is ready
    echo [i] Launching Sovereign Dashboard...
    copy target\wasm32-wasi\release\trueroas.wasm .\trueroas.wasm >nul
    start index.html
) else (
    echo.
    echo ❌ Build failed. Please check your internet connection and try again.
)

pause