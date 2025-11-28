@echo off
REM Windows build script for Brick Collection Manager

echo 🪟 Building Brick Collection Manager for Windows
echo ===============================================

REM Check if uv is available
uv --version >nul 2>&1
if errorlevel 1 (
    echo ❌ uv is required but not installed
    echo 📦 Install uv first: https://github.com/astral-sh/uv"
    exit /b 1
)

REM Sync dependencies using uv
echo 📦 Syncing dependencies with uv...
uv sync

REM Install additional build dependencies
echo 🔧 Installing build dependencies...
uv add --dev pillow pyinstaller

REM Run the build using uv
echo 🚀 Starting build process...
uv run python build.py

echo ✅ Build completed! Check the dist\ directory for your application.
pause
