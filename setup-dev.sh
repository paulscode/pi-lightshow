#!/bin/bash
# Quick setup script for Pi Lightshow development on Linux Mint

echo "=========================================="
echo "Pi Lightshow Development Setup"
echo "=========================================="
echo ""

# Check if running on Linux
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    echo "⚠️  This script is designed for Linux systems"
    echo "You may need to manually install dependencies"
    exit 1
fi

# Update package list
echo "📦 Updating package list..."
sudo apt-get update

# Install system dependencies
echo ""
echo "📦 Installing system dependencies..."
sudo apt-get install -y python3 python3-pip python3-tk vlc

# Check if pip is available
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 not found. Please install python3-pip"
    exit 1
fi

# Install Python packages
echo ""
echo "📦 Installing Python packages..."

# Check if we can use pip or need to use alternative methods
if pip3 install --user python-vlc requests 2>&1 | grep -q "externally-managed-environment"; then
    echo "⚠️  System uses externally-managed Python environment"
    echo "   Trying alternative installation methods..."
    
    # Try using apt packages first
    echo "   Attempting: sudo apt-get install python3-vlc python3-requests"
    sudo apt-get install -y python3-vlc python3-requests 2>/dev/null || true
    
    # If apt didn't work, suggest pipx or venv
    if ! python3 -c "import vlc" 2>/dev/null; then
        echo ""
        echo "⚠️  Could not install via apt. Options:"
        echo "   1) Use pipx (recommended for applications):"
        echo "      sudo apt-get install pipx"
        echo "      pipx install python-vlc"
        echo ""
        echo "   2) Use virtual environment (recommended for development):"
        echo "      python3 -m venv venv"
        echo "      source venv/bin/activate"
        echo "      pip install python-vlc requests"
        echo ""
        echo "   3) Override system protection (not recommended):"
        echo "      pip3 install --user --break-system-packages python-vlc requests"
        echo ""
    fi
else
    echo "✅ Python packages installed"
fi

# Verify installations
echo ""
echo "🔍 Verifying installations..."

python3 -c "import tkinter; print('✅ tkinter OK')" || echo "❌ tkinter failed"
python3 -c "import vlc; print('✅ VLC OK')" || echo "❌ VLC failed (optional)"
python3 -c "import requests; print('✅ requests OK')" || echo "❌ requests failed"

# Check project structure
echo ""
echo "🔍 Checking project structure..."
if [ -d "songs" ]; then
    echo "✅ songs/ directory found"
    echo "   Songs available:"
    ls -1 songs/*.json 2>/dev/null | sed 's/^/   - /' || echo "   (no songs yet)"
else
    echo "❌ songs/ directory not found"
    echo "   Creating it now..."
    mkdir -p songs
fi

if [ -d "src" ]; then
    echo "✅ src/ directory found"
else
    echo "❌ src/ directory not found"
fi

if [ -f "lightshow_v2.py" ]; then
    echo "✅ lightshow_v2.py found"
else
    echo "❌ lightshow_v2.py not found"
fi

# Make lightshow_v2.py executable
if [ -f "lightshow_v2.py" ]; then
    chmod +x lightshow_v2.py
fi

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "To run the simulator:"
echo "  python3 lightshow_v2.py --simulate"
echo ""
echo "For more information:"
echo "  cat README_V2.md"
echo "  cat SETUP_DEV.md"
echo ""
