#!/bin/bash
# macOS/Linux build script for Brick Collection Manager

set -e

echo "🍎 Building Brick Collection Manager for macOS/Linux"
echo "=================================================="

# Check if uv is available
if ! command -v uv &> /dev/null; then
    echo "❌ uv is required but not installed"
    echo "📦 Install uv first: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Sync dependencies using uv
echo "📦 Syncing dependencies with uv..."
uv sync

# Install additional build dependencies
echo "🔧 Installing build dependencies..."
uv add --dev pillow pyinstaller

# Make build script executable
chmod +x build.py

# Run the build using uv
echo "🚀 Starting build process..."
uv run python build.py

echo "✅ Build completed! Check the dist/ directory for your application."