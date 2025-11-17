import asyncio
from edge_tts import Communicate
import os
import re
import tempfile
from pathlib import Path
from .ffmpeg_checker import ensure_ffmpeg_available

def ensure_directories():
    """التأكد من وجود المجلدات المطلوبة."""
    # الحصول على المسار الحالي للبرنامج
    current_dir = os.getcwd()
    
    required_dirs = ["temp", "output"]
    for dir_name in required_dirs:
        dir_path = os.path.join(current_dir, dir_name)
        try:
            if not os.path.exists(dir_path):
                os.makedirs(dir_path, exist_ok=True)
                print(f"✅ تم إنشاء مجلد: {dir_path}")
            else:
                print(f"📁 مجلد موجود: {dir_path}")
        except Exception as e:
            print(f"❌ خطأ في إنشاء مجلد {dir_path}: {e}")

def clean_arabic_text(text: str) -> str:
    """تنظيف النص العربي من الرموز الغريبة."""
    # إزالة الرموز الغريبة
    unwanted_symbols = ['!', '@', '#', '$', '%', '^', '&', '*', '+', '=', '|', '\\', '/', '<', '>', '?', '`', '~']
    
    for symbol in unwanted_symbols:
        text = text.replace(symbol, '')
    
    # إزالة المسافات المتعددة
    text = re.sub(r'\s+', ' ', text)
    
    # تنظيف النص
    text = text.strip()
    
    return text

def get_voices_for_language(language_code: str):
    """
    إرجاع قائمة الأصوات المتاحة للغة معينة مع النوع (ذكر/أنثى) واسم الصوت.
    كل عنصر: { 'name': ..., 'gender': ..., 'display': ... }
    """
    voices = {
        "ar": [
            {"name": "ar-SA-HamedNeural", "gender": "ذكر", "display": "حامد (ذكر سعودي)"},
            {"name": "ar-SA-ZariyahNeural", "gender": "أنثى", "display": "زارية (أنثى سعودية)"}
        ],
        "en": [
            {"name": "en-US-JennyNeural", "gender": "أنثى", "display": "Jenny (أنثى أمريكية)"},
            {"name": "en-US-GuyNeural", "gender": "ذكر", "display": "Guy (ذكر أمريكي)"}
        ],
        "fr": [
            {"name": "fr-FR-DeniseNeural", "gender": "أنثى", "display": "Denise (أنثى فرنسية)"},
            {"name": "fr-FR-HenriNeural", "gender": "ذكر", "display": "Henri (ذكر فرنسي)"}
        ],
        "es": [
            {"name": "es-ES-ElviraNeural", "gender": "أنثى", "display": "Elvira (أنثى إسبانية)"},
            {"name": "es-ES-AlvaroNeural", "gender": "ذكر", "display": "Alvaro (ذكر إسباني)"}
        ],
        "de": [
            {"name": "de-DE-KatjaNeural", "gender": "أنثى", "display": "Katja (أنثى ألمانية)"},
            {"name": "de-DE-ConradNeural", "gender": "ذكر", "display": "Conrad (ذكر ألماني)"}
        ],
        # ... أضف المزيد من اللغات والأصوات حسب الحاجة ...
    }
    # fallback: return at least one default if not found
    return voices.get(language_code, voices.get("en", []))

def get_voice_for_language(language_code: str, gender: str = None) -> str:
    """
    الحصول على صوت مناسب للغة المحددة، مع خيار تحديد النوع (ذكر/أنثى).
    """
    voices = get_voices_for_language(language_code)
    if gender:
        for v in voices:
            if v["gender"] == gender:
                return v["name"]
    # fallback: first voice
    return voices[0]["name"] if voices else "en-US-JennyNeural"

async def generate_audio_for_language(text: str, language_code: str, output_path: str = None, target_duration: float = None, voice_name: str = None):
    """
    توليد صوت لأي لغة من النص المترجم، مع إمكانية تحديد اسم الصوت.
    """
    ensure_directories()
    try:
        if output_path is None:
            output_path = f"temp/audio_{language_code}.mp3"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        # الحصول على الصوت المناسب
        if voice_name is None:
            voice = get_voice_for_language(language_code)
        else:
            voice = voice_name
        print(f"🎤 استخدام الصوت: {voice} للغة {language_code}")
        if language_code == "ar":
            text = clean_arabic_text(text)
        communicate = Communicate(text, voice)
        await communicate.save(output_path)
        print(f"✅ تم حفظ الصوت في: {output_path}")
        try:
            import subprocess
            result = subprocess.run([
                "ffprobe", "-v", "error", "-show_entries",
                "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", output_path
            ], capture_output=True, text=True)
            actual_duration = float(result.stdout.strip())
            print(f"📊 مدة الصوت: {actual_duration:.2f}s")
            if target_duration:
                print(f"📊 مدة الفيديو الأصلي: {target_duration:.2f}s")
                if actual_duration > target_duration:
                    print(f"⚠️ الصوت أطول من الفيديو بـ {actual_duration - target_duration:.2f}s")
                else:
                    print(f"✅ الصوت أقصر من الفيديو بـ {target_duration - actual_duration:.2f}s")
            return True, actual_duration
        except Exception as e:
            print(f"⚠️ تعذر التحقق من مدة الصوت: {e}")
            return True, None
    except Exception as e:
        print(f"❌ خطأ أثناء توليد الصوت: {e}")
        return False, None

async def generate_arabic_audio(text_ar: str, output_path: str = "temp/audio_ar.mp3", target_duration: float = None):
    """توليد صوت عربي من النص المترجم - نسخة مبسطة (للتوافق مع الكود القديم)."""
    return await generate_audio_for_language(text_ar, "ar", output_path, target_duration)

def extend_video_duration(video_path: str, target_duration: float, output_path: str) -> bool:
    """تمديد مدة الفيديو لتناسب مدة الصوت العربي."""
    try:
        import subprocess
        
        # الحصول على مسار ffmpeg
        ffmpeg_path = ensure_ffmpeg_available() or "ffmpeg"
        
        # استخدام ffmpeg لتمديد الفيديو بتكرار الإطار الأخير
        cmd = [
            ffmpeg_path, "-y",
            "-i", video_path,
            "-vf", f"tpad=stop_mode=clone:stop_duration={target_duration}",
            "-af", "apad",
            "-shortest",
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ تم تمديد مدة الفيديو إلى: {target_duration:.2f}s")
            return True
        else:
            print(f"❌ فشل في تمديد مدة الفيديو: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ خطأ أثناء تمديد مدة الفيديو: {e}")
        return False

# للتجربة المباشرة
if __name__ == "__main__":
    sample_text = "مرحبًا بك في برنامج دبلجة الفيديو باستخدام الذكاء الاصطناعي."
    asyncio.run(generate_arabic_audio(sample_text))
