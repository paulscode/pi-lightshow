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

# Check OS version and determine which audio player to use
echo "🔍 Checking Raspberry Pi OS version..."
USE_OMXPLAYER=false
USE_VLC=false

if command -v lsb_release &> /dev/null; then
    OS_VERSION=$(lsb_release -rs 2>/dev/null)
    OS_CODENAME=$(lsb_release -cs 2>/dev/null)
    echo "   Detected: Raspberry Pi OS $OS_VERSION ($OS_CODENAME)"
    
    if [ "$OS_CODENAME" = "buster" ]; then
        echo "   📻 Will use OMXPlayer (legacy, optimized for Buster)"
        USE_OMXPLAYER=true
    else
        echo "   📻 Will use VLC (required for $OS_CODENAME and newer)"
        USE_VLC=true
    fi
else
    # Can't detect version, try both
    echo "   ⚠️  Could not detect OS version, will install both OMXPlayer and VLC"
    USE_OMXPLAYER=true
    USE_VLC=true
fi

# Update package list
echo ""
echo "📦 Updating package list..."
sudo apt-get update

# Install system dependencies
echo ""
echo "📦 Installing system dependencies..."

# Base packages needed for all versions
echo "   Installing base packages: git, python3, python3-pip..."
sudo apt-get install -y git python3 python3-pip

# Install audio player based on OS version
if [ "$USE_OMXPLAYER" = true ]; then
    echo "   Installing OMXPlayer (for Buster)..."
    sudo apt-get install -y omxplayer python3-dbus
fi

if [ "$USE_VLC" = true ]; then
    echo "   Installing VLC (for Bookworm/Trixie and newer)..."
    sudo apt-get install -y vlc python3-vlc
fi

# Check if pip3 is available after installation
if ! command -v pip3 &> /dev/null; then
    echo "⚠️  pip3 still not available, trying to install via python3 -m pip"
fi

# Install Python packages
echo ""
echo "📦 Installing Python packages..."

# Install OMXPlayer wrapper if needed (Buster only)
if [ "$USE_OMXPLAYER" = true ]; then
    echo "   Installing omxplayer-wrapper for OMXPlayer support..."
    
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
fi

# VLC Python bindings should already be installed via python3-vlc package above
if [ "$USE_VLC" = true ]; then
    echo "   ✅ VLC Python bindings installed via python3-vlc package"
fi

# Verify installations
echo ""
echo "🔍 Verifying installations..."

# Check OMXPlayer if expected
if [ "$USE_OMXPLAYER" = true ]; then
    if command -v omxplayer &> /dev/null; then
        echo "✅ omxplayer binary installed"
    else
        echo "❌ omxplayer binary NOT found"
    fi
    
    python3 -c "import dbus; print('✅ dbus (python3-dbus) OK')" 2>/dev/null || echo "❌ dbus module failed"
    
    if python3 -c "import omxplayer.player; print('✅ omxplayer-wrapper OK')" 2>/dev/null; then
        echo "✅ omxplayer-wrapper module OK"
    else
        echo "❌ omxplayer-wrapper module NOT found"
    fi
fi

# Check VLC if expected
if [ "$USE_VLC" = true ]; then
    if command -v vlc &> /dev/null; then
        echo "✅ VLC binary installed"
    else
        echo "❌ VLC binary NOT found"
    fi
    
    if python3 -c "import vlc; print('✅ python3-vlc module OK')" 2>/dev/null; then
        echo "✅ python3-vlc module OK"
    else
        echo "❌ python3-vlc module NOT found"
        echo "   Install with: sudo apt-get install python3-vlc"
    fi
fi

# Summary
echo ""
if [ "$USE_OMXPLAYER" = true ] || [ "$USE_VLC" = true ]; then
    echo "Audio player status:"
    if [ "$USE_OMXPLAYER" = true ]; then
        echo "   - OMXPlayer: For Raspbian Buster (legacy)"
    fi
    if [ "$USE_VLC" = true ]; then
        echo "   - VLC: For newer Raspberry Pi OS (Bookworm, Trixie, etc.)"
    fi
else
    echo "⚠️  No audio player configured - lightshow will run in simulated mode"
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
