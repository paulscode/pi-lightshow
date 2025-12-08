#!/bin/bash
# Setup script for the Song Editor development environment

echo "Setting up Pi Lightshow Song Editor..."

# Check if running on Raspberry Pi (should NOT install editor deps there)
if grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
    echo "WARNING: This script is for development PCs only."
    echo "The song editor should not be installed on the Raspberry Pi."
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check for ffmpeg (required by pydub for MP3 processing)
if ! command -v ffmpeg &> /dev/null; then
    echo ""
    echo "WARNING: ffmpeg not found!"
    echo "The editor requires ffmpeg for audio processing."
    echo ""
    echo "To install on Linux Mint/Ubuntu:"
    echo "  sudo apt-get install ffmpeg"
    echo ""
    read -p "Install ffmpeg now? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        sudo apt-get update
        sudo apt-get install -y ffmpeg
    fi
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv-editor" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv-editor
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to create virtual environment."
        echo "You may need to install python3-venv:"
        echo "  sudo apt-get install python3-venv"
        exit 1
    fi
fi

# Activate virtual environment and install dependencies
echo "Installing editor dependencies in virtual environment..."
source venv-editor/bin/activate
pip install --upgrade pip
pip install -r requirements-editor.txt

if [ $? -eq 0 ]; then
    echo ""
    echo "✓ Setup complete!"
    echo ""
    echo "To run the song editor:"
    echo "  ./start-editor.sh"
    echo ""
    echo "Or manually:"
    echo "  source venv-editor/bin/activate"
    echo "  python3 song_editor.py"
    echo ""
else
    echo ""
    echo "ERROR: Failed to install dependencies."
    echo "Please check the error messages above."
    exit 1
fi
