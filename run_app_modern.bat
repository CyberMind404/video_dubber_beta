@echo off
chcp 65001 >nul
title Video Dubber AI - Multi-Language Dubbing
echo.
echo ========================================
echo    Video Dubber AI - Multi-Language Dubbing
echo ========================================
echo.
echo 🌍 دعم الدبلجة من أي لغة إلى أي لغة
echo 🎬 اكتشاف تلقائي للغة الفيديو
echo 🔊 توليد صوت طبيعي لأي لغة
echo.
echo جاري تشغيل التطبيق...
echo.

echo 🔍 فحص البيئة...
python --version
echo.

echo 🚀 تشغيل التطبيق مع دعم اكتشاف اللغة...
echo.

REM تشغيل التطبيق مع تسجيل مفصل
python main.py

if %errorlevel% neq 0 (
    echo.
    echo ❌ حدث خطأ أثناء تشغيل التطبيق
    echo.
    pause
)

echo.
echo ✅ انتهى تشغيل التطبيق
pause 