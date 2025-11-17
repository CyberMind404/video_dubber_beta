@echo off
chcp 65001 >nul
echo ========================================
echo  Video Dubber AI - تثبيت المتطلبات
echo ========================================
echo.
echo جاري تثبيت جميع الحزم المطلوبة...
echo.
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo ❌ حدث خطأ أثناء تثبيت الحزم!
    pause
    exit /b 1
)
echo.
echo ✅ تم تثبيت جميع الحزم بنجاح!
echo ========================================
echo.
echo ========================================
echo  فحص وتثبيت ffmpeg تلقائياً
setlocal EnableDelayedExpansion
set FFMPEG_PATH=ffmpeg.exe
where %FFMPEG_PATH% >nul 2>nul
if %errorlevel% neq 0 (
    echo لم يتم العثور على ffmpeg. سيتم تحميله الآن...
    powershell -Command "Invoke-WebRequest -Uri https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip -OutFile ffmpeg.zip"
    powershell -Command "Expand-Archive -Path ffmpeg.zip -DestinationPath ."
    for /d %%i in (ffmpeg-*) do set FFMPEG_DIR=%%i
    copy "%FFMPEG_DIR%\bin\ffmpeg.exe" . >nul
    del /q ffmpeg.zip
    rmdir /s /q %FFMPEG_DIR%
    echo ✅ تم تحميل وتثبيت ffmpeg بنجاح!
) else (
    echo ✅ ffmpeg مثبت بالفعل على جهازك.
)
echo ========================================
pause 