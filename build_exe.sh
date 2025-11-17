#!/bin/bash

echo "========================================"
echo "Video Dubber AI - Building EXE"
echo "========================================"

echo ""
echo "1. Installing PyInstaller..."
pip install pyinstaller

echo ""
echo "2. Building EXE with all dependencies..."
pyinstaller --onefile \
            --windowed \
            --icon=video-dubber.ico \
            --add-data "assets:assets" \
            --add-data "ui:ui" \
            --add-data "core:core" \
            --hidden-import=PyQt6.QtCore \
            --hidden-import=PyQt6.QtWidgets \
            --hidden-import=PyQt6.QtGui \
            --hidden-import=edge_tts \
            --hidden-import=whisper \
            --hidden-import=requests \
            --hidden-import=simpleaudio \
            --hidden-import=asyncio \
            --name="VideoDubberAI" \
            main.py

echo ""
echo "3. Copying additional files..."
mkdir -p dist/assets/sounds
cp assets/sounds/*.wav dist/assets/sounds/

echo ""
echo "4. Creating temp and output directories..."
mkdir -p dist/temp
mkdir -p dist/output

echo ""
echo "========================================"
echo "✅ Build completed!"
echo "========================================"
echo ""
echo "The EXE file is located in: dist/VideoDubberAI"
echo ""
echo "To run the application:"
echo "1. Navigate to the dist folder"
echo "2. Run ./VideoDubberAI"
echo "3. The app will automatically install ffmpeg on first run"
echo "" 