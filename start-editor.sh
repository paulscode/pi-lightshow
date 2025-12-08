#!/bin/bash
# Quick Start Guide for Song Editor
# This script helps you get started with the editor

echo "╔════════════════════════════════════════════════════════════╗"
echo "║        Pi Lightshow Song Editor - Quick Start             ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Check if running on Raspberry Pi
if grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
    echo "⚠️  WARNING: You are running on a Raspberry Pi"
    echo "   The song editor is designed for development PCs only."
    echo "   It requires large dependencies that are not needed on the Pi."
    echo ""
    exit 1
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3."
    exit 1
fi
echo "✓ Python 3 found"

# Check tkinter
if ! python3 -c "import tkinter" 2>/dev/null; then
    echo "❌ tkinter not found. Install with:"
    echo "   sudo apt-get install python3-tk"
    exit 1
fi
echo "✓ tkinter found"

# Check ffmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo "⚠️  ffmpeg not found (required for audio processing)"
    echo "   Install with: sudo apt-get install ffmpeg"
else
    echo "✓ ffmpeg found"
fi

# Check for virtual environment
if [ ! -d "venv-editor" ]; then
    echo ""
    echo "Virtual environment not found."
    read -p "Run setup now? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        ./setup-editor.sh
        if [ $? -ne 0 ]; then
            echo "Setup failed. Please fix errors and try again."
            exit 1
        fi
    else
        echo ""
        echo "To install, run:"
        echo "  ./setup-editor.sh"
        echo ""
        exit 1
    fi
fi

# Check editor dependencies in venv
DEPS_INSTALLED=true

if ! venv-editor/bin/python -c "import pygame" 2>/dev/null; then
    echo "⚠️  pygame not installed in venv"
    DEPS_INSTALLED=false
fi

if ! venv-editor/bin/python -c "import pydub" 2>/dev/null; then
    echo "⚠️  pydub not installed in venv"
    DEPS_INSTALLED=false
fi

if ! venv-editor/bin/python -c "import numpy" 2>/dev/null; then
    echo "⚠️  numpy not installed in venv"
    DEPS_INSTALLED=false
fi

if [ "$DEPS_INSTALLED" = false ]; then
    echo ""
    echo "Editor dependencies are incomplete."
    read -p "Re-run setup? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        ./setup-editor.sh
    else
        echo ""
        echo "To install later, run:"
        echo "  ./setup-editor.sh"
        echo ""
        exit 1
    fi
else
    echo "✓ Editor dependencies installed"
fi

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                 Everything is ready!                       ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "Starting song editor..."
echo "(Use Help → Quick Start for tips and documentation)"
echo ""
source venv-editor/bin/activate
python3 song_editor.py
