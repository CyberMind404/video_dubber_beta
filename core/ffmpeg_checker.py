import subprocess
import os
import sys
import platform
import requests
import zipfile
import shutil
from pathlib import Path

def check_ffmpeg_installed():
    """التحقق من وجود ffmpeg في النظام."""
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True, timeout=10)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
        return False

def get_ffmpeg_download_url():
    """الحصول على رابط تحميل ffmpeg المناسب للنظام."""
    system = platform.system().lower()
    machine = platform.machine().lower()
    
    if system == "windows":
        if "64" in machine or "x86_64" in machine:
            return "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl-shared.zip"
        else:
            return "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win32-gpl-shared.zip"
    elif system == "darwin":  # macOS
        return "https://evermeet.cx/ffmpeg/getrelease/zip"
    else:  # Linux
        return "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
    
    return None

def download_and_extract_ffmpeg():
    """تحميل وتثبيت ffmpeg تلقائيًا."""
    try:
        print("🔍 فحص وجود ffmpeg...")
        
        if check_ffmpeg_installed():
            print("✅ ffmpeg موجود بالفعل في النظام")
            return True
            
        print("❌ ffmpeg غير موجود، جاري التحميل...")
        
        # إنشاء مجلد ffmpeg في مجلد التطبيق
        app_dir = Path(__file__).parent.parent
        ffmpeg_dir = app_dir / "ffmpeg"
        ffmpeg_dir.mkdir(exist_ok=True)
        
        # الحصول على رابط التحميل
        download_url = get_ffmpeg_download_url()
        if not download_url:
            print("❌ لا يمكن تحديد رابط تحميل مناسب لهذا النظام")
            return False
            
        # تحميل الملف
        print(f"📥 جاري تحميل ffmpeg من: {download_url}")
        response = requests.get(download_url, stream=True)
        response.raise_for_status()
        
        # حفظ الملف
        zip_path = ffmpeg_dir / "ffmpeg.zip"
        with open(zip_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print("📦 جاري استخراج الملف...")
        
        # استخراج الملف
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(ffmpeg_dir)
        
        # حذف ملف ZIP
        zip_path.unlink()
        
        # البحث عن ملف ffmpeg.exe في المجلدات المستخرجة
        ffmpeg_exe = None
        for root, dirs, files in os.walk(ffmpeg_dir):
            for file in files:
                if file == "ffmpeg.exe":
                    ffmpeg_exe = Path(root) / file
                    break
            if ffmpeg_exe:
                break
        
        if not ffmpeg_exe:
            print("❌ لم يتم العثور على ffmpeg.exe في الملفات المستخرجة")
            return False
        
        # نسخ ffmpeg إلى مجلد التطبيق
        final_ffmpeg_path = app_dir / "ffmpeg.exe"
        shutil.copy2(ffmpeg_exe, final_ffmpeg_path)
        
        # حذف مجلد التحميل المؤقت
        shutil.rmtree(ffmpeg_dir)
        
        print("✅ تم تثبيت ffmpeg بنجاح!")
        return True
        
    except Exception as e:
        print(f"❌ خطأ أثناء تثبيت ffmpeg: {e}")
        return False

def get_ffmpeg_path():
    """الحصول على مسار ffmpeg."""
    # أولاً، تحقق من وجود ffmpeg في النظام
    if check_ffmpeg_installed():
        return "ffmpeg"
    
    # ثانياً، تحقق من وجود ffmpeg في مجلد التطبيق
    app_dir = Path(__file__).parent.parent
    local_ffmpeg = app_dir / "ffmpeg.exe"
    
    if local_ffmpeg.exists():
        return str(local_ffmpeg)
    
    # ثالثاً، حاول التثبيت التلقائي
    if download_and_extract_ffmpeg():
        return str(local_ffmpeg)
    
    # إذا فشل كل شيء، استخدم المسار الافتراضي
    return r"C:\ffmpeg-master-latest-win64-gpl-shared\bin\ffmpeg.exe"

def ensure_ffmpeg_available():
    """التأكد من توفر ffmpeg وتثبيته إذا لزم الأمر."""
    print("🔧 فحص وتثبيت ffmpeg...")
    
    ffmpeg_path = get_ffmpeg_path()
    
    # اختبار ffmpeg
    try:
        result = subprocess.run([ffmpeg_path, '-version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ ffmpeg يعمل بشكل صحيح")
            return ffmpeg_path
        else:
            print("❌ ffmpeg لا يعمل بشكل صحيح")
            return None
    except Exception as e:
        print(f"❌ خطأ في اختبار ffmpeg: {e}")
        return None

if __name__ == "__main__":
    # اختبار الدالة
    path = ensure_ffmpeg_available()
    if path:
        print(f"✅ ffmpeg متاح في: {path}")
    else:
        print("❌ فشل في تثبيت ffmpeg") 