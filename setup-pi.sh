#!/bin/bash
# Setup script for Pi Lightshow on Raspberry Pi

echo "=========================================="
echo "Pi Lightshow - Raspberry Pi Setup"
echo "=========================================="
echo ""

# Check if running on Raspberry Pi
if [ ! -f /proc/device-tree/model ]; then
    echo "⚠️  Warning: Cannot detect if this is a Raspberry Pi"
    echo "This script is designed for Raspberry Pi hardware"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
elif ! grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
    echo "⚠️  Warning: This doesn't appear to be a Raspberry Pi"
    echo "This script is designed for Raspberry Pi hardware"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check OS version and warn about OMXPlayer compatibility
echo "🔍 Checking Raspberry Pi OS version..."
if command -v lsb_release &> /dev/null; then
    OS_VERSION=$(lsb_release -rs 2>/dev/null)
    OS_CODENAME=$(lsb_release -cs 2>/dev/null)
    echo "   Detected: Raspberry Pi OS $OS_VERSION ($OS_CODENAME)"
    
    if [ "$OS_CODENAME" != "buster" ]; then
        echo ""
        echo "⚠️  WARNING: OMXPlayer is only available on Raspbian Buster (legacy)"
        echo "   Your system is running: $OS_CODENAME"
        echo "   OMXPlayer installation may fail on newer versions"
        echo ""
        read -p "Continue anyway? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
fi

# Update package list
echo ""
echo "📦 Updating package list..."
sudo apt-get update

# Install system dependencies
echo ""
echo "📦 Installing system dependencies..."
echo "   This includes: git, omxplayer, python3, and related tools"
sudo apt-get install -y git omxplayer python3 python3-pip python3-dbus

# Check if pip3 is available after installation
if ! command -v pip3 &> /dev/null; then
    echo "⚠️  pip3 still not available, trying to install via python3 -m pip"
fi

# Install Python packages
echo ""
echo "📦 Installing Python packages for OMXPlayer..."

# Try different installation methods in order of preference
INSTALL_SUCCESS=false

# Method 1: Try apt packages (system packages are more reliable)
echo "   Trying system packages (apt)..."
if sudo apt-get install -y python3-dbus 2>/dev/null; then
    echo "   ✅ python3-dbus installed via apt"
fi

# Method 2: Try pip3 --user
if command -v pip3 &> /dev/null; then
    echo "   Trying pip3 --user..."
    if pip3 install --user omxplayer-wrapper 2>/dev/null; then
        INSTALL_SUCCESS=true
        echo "   ✅ omxplayer-wrapper installed via pip3 --user"
    fi
fi

# Method 3: Try python3 -m pip --user
if [ "$INSTALL_SUCCESS" = false ]; then
    echo "   Trying python3 -m pip --user..."
    if python3 -m pip install --user omxplayer-wrapper 2>/dev/null; then
        INSTALL_SUCCESS=true
        echo "   ✅ omxplayer-wrapper installed via python3 -m pip --user"
    fi
fi

# Method 4: Try with --break-system-packages if on newer OS
if [ "$INSTALL_SUCCESS" = false ]; then
    echo "   Trying pip3 with --break-system-packages..."
    if pip3 install --user --break-system-packages omxplayer-wrapper 2>/dev/null; then
        INSTALL_SUCCESS=true
        echo "   ✅ omxplayer-wrapper installed with --break-system-packages"
    fi
fi

if [ "$INSTALL_SUCCESS" = false ]; then
    echo "   ⚠️  Automated installation failed. Manual installation required:"
    echo "      pip3 install --user omxplayer-wrapper"
    echo "      or: python3 -m pip install --user omxplayer-wrapper"
fi

# Verify installations
echo ""
echo "🔍 Verifying installations..."

# Check OMXPlayer binary
if command -v omxplayer &> /dev/null; then
    echo "✅ omxplayer binary installed"
else
    echo "❌ omxplayer binary NOT found"
    echo "   This is required for audio playback on Raspberry Pi"
fi

# Check Python packages
python3 -c "import dbus; print('✅ dbus (python3-dbus) OK')" 2>/dev/null || echo "❌ dbus module failed"

if python3 -c "import omxplayer.player; print('✅ omxplayer-wrapper OK')" 2>/dev/null; then
    echo "✅ omxplayer-wrapper module OK"
else
    echo "❌ omxplayer-wrapper module NOT found"
    echo "   The lightshow will fall back to simulated mode without audio"
fi

# Check if config file exists
echo ""
echo "🔍 Checking configuration..."
if [ -f "config.json" ]; then
    echo "✅ config.json found"
else
    if [ -f "config-example.json" ]; then
        echo "⚠️  config.json not found"
        echo "   Copy config-example.json to config.json and customize it:"
        echo "   cp config-example.json config.json"
    else
        echo "⚠️  No config files found"
    fi
fi

# Check project structure
echo ""
echo "🔍 Checking project structure..."
if [ -d "songs" ]; then
    echo "✅ songs/ directory found"
    SONG_COUNT=$(ls -1 songs/*.json 2>/dev/null | grep -v playlist.json | wc -l)
    if [ "$SONG_COUNT" -gt 0 ]; then
        echo "   Songs available ($SONG_COUNT):"
        ls -1 songs/*.json 2>/dev/null | grep -v playlist.json | sed 's/^/   - /'
    else
        echo "   ⚠️  No song files found (add .json files to songs/)"
    fi
else
    echo "❌ songs/ directory not found"
fi

if [ -d "src" ]; then
    echo "✅ src/ directory found"
else
    echo "❌ src/ directory not found - project structure incomplete"
fi

# Final summary
echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Make sure you have song JSON files in the songs/ directory"
echo "2. Make sure you have MP3 files matching your song definitions"
echo "3. Create/edit config.json with your GPIO pin mappings"
echo "4. Test the lightshow:"
echo "   python3 lightshow.py"
echo ""
echo "For more information, see README.md"
echo ""
