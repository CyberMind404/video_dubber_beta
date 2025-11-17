import subprocess
import os
import tempfile
import time
from pathlib import Path
from .ffmpeg_checker import ensure_ffmpeg_available

# الحصول على مسار ffmpeg ديناميكيًا
FFMPEG_PATH = ensure_ffmpeg_available() or "ffmpeg"

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

def extract_audio(video_path: str, output_audio_path: str = "temp/audio.wav") -> bool:
    """استخراج الصوت من ملف فيديو وحفظه كملف صوتي."""
    ensure_directories()
    
    print(f"Trying to extract audio from: {video_path} to {output_audio_path}")
    
    # التأكد من وجود الفيديو
    if not os.path.exists(video_path):
        print(f"❌ ملف الفيديو غير موجود: {video_path}")
        return False
    
    try:
        # إنشاء المجلد إذا لم يكن موجوداً
        output_dir = os.path.dirname(output_audio_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
            print(f"✅ تم إنشاء مجلد: {output_dir}")
        
        # حذف الملف القديم إذا كان موجوداً
        if os.path.exists(output_audio_path):
            os.remove(output_audio_path)
            print(f"🗑️ تم حذف الملف القديم: {output_audio_path}")
        
        print("About to call ffmpeg...")
        
        # استخدام مسار مطلق للفيديو
        video_path_abs = os.path.abspath(video_path)
        output_audio_path_abs = os.path.abspath(output_audio_path)
        
        result = subprocess.run([
            FFMPEG_PATH, "-y",
            "-i", video_path_abs,
            "-vn",  # لا فيديو
            "-acodec", "pcm_s16le",  # ترميز صوتي متوافق
            "-ar", "16000",  # معدل عينات متوافق مع Whisper
            "-ac", "1",  # قناة صوت واحدة
            output_audio_path_abs
        ], check=True, capture_output=True, text=True, timeout=300)
        
        print("ffmpeg call finished.")
        
        # التحقق من وجود الملف بعد الاستخراج
        if os.path.exists(output_audio_path_abs):
            file_size = os.path.getsize(output_audio_path_abs)
            print(f"✅ تم استخراج الصوت بنجاح: {output_audio_path_abs}")
            print(f"📊 حجم الملف: {file_size} bytes")
            
            # انتظار قصير للتأكد من اكتمال الكتابة
            time.sleep(1)
            
            return True
        else:
            print(f"❌ فشل في إنشاء ملف الصوت: {output_audio_path_abs}")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"❌ خطأ أثناء استخراج الصوت: {e}")
        print(f"ffmpeg stdout: {e.stdout}")
        print(f"ffmpeg stderr: {e.stderr}")
        return False
    except subprocess.TimeoutExpired:
        print(f"❌ انتهت مهلة استخراج الصوت")
        return False
    except Exception as e:
        print(f"❌ خطأ غير متوقع أثناء استخراج الصوت: {e}")
        return False

def merge_audio_with_video(
    original_video: str, new_audio: str, output_path: str = "output/final_video.mp4"
) -> bool:
    """دمج ملف صوتي جديد مع فيديو وحفظ الناتج."""
    ensure_directories()
    
    print(f"Trying to merge: {original_video} + {new_audio} -> {output_path}")
    
    # التحقق من وجود الملفات
    if not os.path.exists(original_video):
        print(f"❌ ملف الفيديو الأصلي غير موجود: {original_video}")
        return False
    
    if not os.path.exists(new_audio):
        print(f"❌ ملف الصوت الجديد غير موجود: {new_audio}")
        return False
    
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        print("About to call ffmpeg for merging...")
        
        # استخدام مسارات مطلقة
        original_video_abs = os.path.abspath(original_video)
        new_audio_abs = os.path.abspath(new_audio)
        output_path_abs = os.path.abspath(output_path)
        
        result = subprocess.run([
            FFMPEG_PATH, "-y",
            "-i", original_video_abs,
            "-i", new_audio_abs,
            "-c:v", "copy",
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-shortest",
            output_path_abs
        ], check=True, capture_output=True, text=True, timeout=600)
        
        print("ffmpeg merge call finished.")
        
        if os.path.exists(output_path_abs):
            file_size = os.path.getsize(output_path_abs)
            print(f"✅ تم دمج الصوت مع الفيديو بنجاح: {output_path_abs}")
            print(f"📊 حجم الملف النهائي: {file_size} bytes")
            
            # حذف ملف الصوت المؤقت بعد الدمج
            try:
                os.remove(new_audio_abs)
                print(f"[merge_audio_with_video] Deleted temp audio: {new_audio_abs}")
            except Exception as e:
                print(f"[merge_audio_with_video] Failed to delete temp audio: {e}")
            
            return True
        else:
            print(f"❌ فشل في إنشاء الفيديو النهائي: {output_path_abs}")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"❌ خطأ أثناء دمج الصوت مع الفيديو: {e}")
        print(f"ffmpeg stdout: {e.stdout}")
        print(f"ffmpeg stderr: {e.stderr}")
        return False
    except subprocess.TimeoutExpired:
        print(f"❌ انتهت مهلة دمج الصوت مع الفيديو")
        return False
    except Exception as e:
        print(f"❌ خطأ غير متوقع أثناء دمج الصوت مع الفيديو: {e}")
        return False
