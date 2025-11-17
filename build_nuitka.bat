@echo off
echo ========================================
echo Video Dubber AI - Building with Nuitka
echo ========================================

echo.
echo 1. Installing Nuitka and dependencies...
pip install nuitka
pip install zstandard

echo.
echo 2. Building with Nuitka (Professional Build)...
nuitka --mingw64 ^
        --onefile ^
        --standalone ^
        --windows-disable-console ^
        --enable-plugin=pyqt6 ^
        --disable-plugin=numpy ^
        --disable-plugin=torch ^
        --nofollow-import-to=numba ^
        --module-parameter=torch-disable-jit=yes ^
        --module-parameter=numba-disable-jit=yes ^
        --include-data-dir=assets=assets ^
        --include-data-dir=core=core ^
        --include-data-dir=ui=ui ^
        --windows-icon-from-ico=video-dubber.ico ^
        --windows-company-name="Abdallah Software" ^
        --windows-product-name="Video Dubber AI" ^
        --windows-product-version="1.0.0" ^
        --windows-file-version="1.0.0" ^
        --windows-file-description="Video Dubber AI - Smart Video Dubbing Application" ^
        --windows-uac-admin ^
        --assume-yes-for-downloads ^
        --show-progress ^
        --show-memory ^
        --remove-output ^
        --output-dir=dist ^
        --output-filename=VideoDubberAI.exe ^
        main.py

echo.
echo 3. Creating required directories...
if not exist "dist\temp" mkdir "dist\temp"
if not exist "dist\output" mkdir "dist\output"

echo.
echo 4. Copying additional files...
if not exist "dist\assets" mkdir "dist\assets"
if not exist "dist\assets\sounds" mkdir "dist\assets\sounds"
copy "assets\sounds\*.wav" "dist\assets\sounds\"

echo.
echo ========================================
echo ✅ Nuitka Build completed!
echo ========================================
echo.
echo The EXE file is located in: dist\VideoDubberAI.exe
echo.
echo Features of this build:
echo - Single executable file
echo - No console window
echo - Professional Windows metadata
echo - Optimized for PyQt6
echo - Automatic ffmpeg installation
echo - All assets included
echo.
echo To run the application:
echo 1. Navigate to the dist folder
echo 2. Double-click VideoDubberAI.exe
echo 3. The app will automatically install ffmpeg on first run
echo.
pause 