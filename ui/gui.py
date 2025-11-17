#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
نسخة تشخيصية من تطبيق دبلجة الفيديو
مع معالجة أفضل للأخطاء وتسجيل مفصل
"""

import os
import sys
import asyncio
import time
import subprocess
import logging
import traceback
import shutil
from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QLabel, QVBoxLayout, QHBoxLayout,
    QFileDialog, QTextEdit, QMessageBox, QGraphicsDropShadowEffect, QProgressBar, QComboBox
)
from PyQt6.QtCore import QFile, QTextStream, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QIcon, QDragEnterEvent, QDropEvent

# إعداد التسجيل المفصل
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('debug_app.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# استيراد الوحدات مع معالجة الأخطاء
try:
    from ui.animations import fade_in_widget
    logger.info("✅ تم استيراد animations بنجاح")
except Exception as e:
    logger.error(f"❌ خطأ في استيراد animations: {e}")
    fade_in_widget = lambda x: None

try:
    from core.audio_handler import extract_audio, merge_audio_with_video, ensure_directories
    logger.info("✅ تم استيراد audio_handler بنجاح")
except Exception as e:
    logger.error(f"❌ خطأ في استيراد audio_handler: {e}")

try:
    from core.speech_to_text import transcribe_audio, is_whisper_model_downloaded, transcribe_with_language_detection
    logger.info("✅ تم استيراد speech_to_text بنجاح")
except Exception as e:
    logger.error(f"❌ خطأ في استيراد speech_to_text: {e}")

try:
    from core.translator import translate_text_simple, translate_text_general, get_language_name, detect_language_from_text
    logger.info("✅ تم استيراد translator بنجاح")
except Exception as e:
    logger.error(f"❌ خطأ في استيراد translator: {e}")

try:
    from core.text_to_speech import generate_arabic_audio, extend_video_duration, generate_audio_for_language, get_voices_for_language
    logger.info("✅ تم استيراد text_to_speech بنجاح")
except Exception as e:
    logger.error(f"❌ خطأ في استيراد text_to_speech: {e}")

try:
    import simpleaudio as sa
    logger.info("✅ تم استيراد simpleaudio بنجاح")
except Exception as e:
    logger.error(f"❌ خطأ في استيراد simpleaudio: {e}")

try:
    from core.ffmpeg_checker import ensure_ffmpeg_available
    logger.info("✅ تم استيراد ffmpeg_checker بنجاح")
except Exception as e:
    logger.error(f"❌ خطأ في استيراد ffmpeg_checker: {e}")

class DebugPipelineWorker(QThread):
    """خيط منفصل لمعالجة خط الدبلجة مع تسجيل مفصل للأخطاء."""
    success = pyqtSignal(str)
    error = pyqtSignal(str)
    transcript_ready = pyqtSignal(str)
    finished = pyqtSignal()
    final_video_path = pyqtSignal(str)
    video_duration_ready = pyqtSignal(float)
    model_loading = pyqtSignal(str)
    stopped = pyqtSignal()
    progress = pyqtSignal(int, float, str)
    language_detected = pyqtSignal(str)

    def __init__(self, video_path, target_language="ar", whisper_model="medium", voice_name=None, source_language=None):
        super().__init__()
        self.video_path = video_path
        self.target_language = target_language
        self.whisper_model = whisper_model
        self.voice_name = voice_name  # <--- أضفت هذا السطر
        self.source_language = source_language
        self._should_stop = False
        self.whisper_proc = None
        logger.info(f"🚀 تم إنشاء PipelineWorker مع الفيديو: {video_path}")
        logger.info(f"🌍 اللغة المستهدفة: {target_language}")
        logger.info(f"🌍 اللغة الأصلية: {source_language}")

    def stop(self):
        """إيقاف آمن للخيط."""
        logger.info("🛑 طلب إيقاف المعالجة...")
        self._should_stop = True
        if hasattr(self, 'whisper_proc') and self.whisper_proc and self.whisper_proc.poll() is None:
            try:
                logger.info("🛑 إيقاف عملية Whisper...")
                self.whisper_proc.terminate()
                self.whisper_proc.wait(timeout=5)
                if self.whisper_proc.poll() is None:
                    logger.warning("🛑 إجبار إغلاق عملية Whisper...")
                    self.whisper_proc.kill()
            except Exception as e:
                logger.error(f"❌ خطأ في إيقاف عملية Whisper: {e}")

    def cleanup(self):
        """تنظيف الموارد."""
        try:
            if hasattr(self, 'whisper_proc') and self.whisper_proc:
                if self.whisper_proc.poll() is None:
                    logger.info("🧹 تنظيف عملية Whisper...")
                    self.whisper_proc.terminate()
                    self.whisper_proc.wait(timeout=3)
        except Exception as e:
            logger.error(f"❌ خطأ في التنظيف: {e}")

    def run(self):
        """تشغيل خط المعالجة مع تسجيل مفصل."""
        try:
            logger.info("🚀 بدء خط المعالجة...")
            
            # التأكد من وجود المجلدات المطلوبة
            logger.info("📁 إنشاء المجلدات المطلوبة...")
            ensure_directories()
            
            audio_path = "temp/audio.wav"
            arabic_audio = "temp/audio_ar.mp3"
            base, ext = os.path.splitext(os.path.basename(self.video_path))
            # احصل على اسم اللغة المستهدفة الكامل
            target_language_full = self.target_language
            if hasattr(self, 'supported_languages'):
                target_language_full = self.supported_languages.get(self.target_language, self.target_language)
            else:
                # نسخة احتياطية: جلب الأسماء من نفس القاموس المستخدم في DubberApp
                target_language_map = {
                    "ar": "Arabic", "en": "English", "fr": "French", "es": "Spanish", "de": "German", "it": "Italian", "pt": "Portuguese", "ru": "Russian", "zh": "Chinese", "ja": "Japanese", "ko": "Korean", "hi": "Hindi", "tr": "Turkish", "nl": "Dutch", "pl": "Polish", "sv": "Swedish", "da": "Danish", "no": "Norwegian", "fi": "Finnish", "he": "Hebrew", "fa": "Persian", "ur": "Urdu", "bn": "Bengali", "th": "Thai", "vi": "Vietnamese", "id": "Indonesian", "ms": "Malay"
                }
                target_language_full = target_language_map.get(self.target_language, self.target_language)
            # اسم الفيديو النهائي
            final_video = os.path.join("output", f"{base}_{target_language_full}{ext}")

            logger.info(f"📂 مسارات الملفات:")
            logger.info(f"   الفيديو: {self.video_path}")
            logger.info(f"   الصوت: {audio_path}")
            logger.info(f"   الصوت العربي: {arabic_audio}")
            logger.info(f"   الفيديو النهائي: {final_video}")

            # التحقق من وجود الفيديو
            if not os.path.exists(self.video_path):
                error_msg = f"❌ ملف الفيديو غير موجود: {self.video_path}"
                logger.error(error_msg)
                self.error.emit(error_msg)
                return

            # استخراج مدة الفيديو
            logger.info("⏱️ استخراج مدة الفيديو...")
            duration = self.get_video_duration(self.video_path)
            if duration:
                logger.info(f"⏱️ مدة الفيديو: {duration:.2f} ثانية")
                self.video_duration_ready.emit(duration)
            else:
                logger.warning("⚠️ لم يتم تحديد مدة الفيديو")

            # 1. استخراج الصوت
            logger.info("🎤 استخراج الصوت من الفيديو...")
            self.progress.emit(10, 0, "استخراج الصوت")
            
            if not extract_audio(self.video_path, audio_path):
                error_msg = "❌ فشل في استخراج الصوت من الفيديو"
                logger.error(error_msg)
                self.error.emit(error_msg)
                return

            # التحقق من وجود ملف الصوت
            if not os.path.exists(audio_path):
                error_msg = f"❌ ملف الصوت غير موجود بعد الاستخراج: {audio_path}"
                logger.error(error_msg)
                self.error.emit(error_msg)
                return

            logger.info(f"✅ تم استخراج الصوت بنجاح: {audio_path}")
            self.progress.emit(20, 0, "استخراج الصوت")

            if self._should_stop:
                logger.info("🛑 تم إيقاف المعالجة بعد استخراج الصوت")
                self.stopped.emit()
                return

            # 2. تحويل الصوت إلى نص (Whisper) مع اكتشاف اللغة
            logger.info("🎤 بدء تحويل الصوت إلى نص مع اكتشاف اللغة...")
            self.progress.emit(30, 0, "تحويل الصوت إلى نص")
            
            if not is_whisper_model_downloaded(self.whisper_model):
                logger.info(f"📥 تحميل نموذج Whisper ({self.whisper_model})...")
                self.model_loading.emit(f"Loading Whisper model ({self.whisper_model})... This may take a while on first use.")
            else:
                logger.info(f"✅ نموذج Whisper ({self.whisper_model}) متاح")
                self.model_loading.emit("")

            whisper_txt = os.path.join("temp", "audio.txt")
            if os.path.exists(whisper_txt):
                os.remove(whisper_txt)
                logger.info("🗑️ حذف ملف النص القديم")

            try:
                # استخدام مسار مطلق لملف الصوت
                audio_path_abs = os.path.abspath(audio_path)
                logger.info(f"🎤 بدء تشغيل Whisper مع اكتشاف اللغة: {audio_path_abs}")
                
                whisper_cmd = [
                    sys.executable, "-m", "whisper", 
                    audio_path_abs, 
                    "--model", self.whisper_model, 
                    "--output_format", "txt", 
                    "--output_dir", "temp"
                ]
                logger.info(f"🔧 أمر Whisper: {' '.join(whisper_cmd)}")
                
                self.whisper_proc = subprocess.Popen(
                    whisper_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                whisper_start = time.time()
                while self.whisper_proc.poll() is None:
                    if self._should_stop:
                        logger.info("🛑 إيقاف عملية Whisper...")
                        self.whisper_proc.terminate()
                        self.stopped.emit()
                        return
                    
                    elapsed = time.time() - whisper_start
                    est_total = max(duration * 0.7, 30) if duration else 60
                    percent = 30 + 40 * min(elapsed / est_total, 1)
                    eta = max(est_total - elapsed, 0)
                    self.progress.emit(int(percent), eta / 60, "تحويل الصوت إلى نص")
                    time.sleep(1)
                
                if self._should_stop:
                    logger.info("🛑 تم إيقاف المعالجة أثناء Whisper")
                    self.stopped.emit()
                    return
                    
                # التحقق من نجاح العملية
                if self.whisper_proc.returncode != 0:
                    stdout, stderr = self.whisper_proc.communicate()
                    error_msg = f"❌ فشل في تحويل الصوت إلى نص. رمز الخطأ: {self.whisper_proc.returncode}"
                    logger.error(error_msg)
                    logger.error(f"stdout: {stdout}")
                    logger.error(f"stderr: {stderr}")
                    self.error.emit(error_msg)
                    return
                    
                logger.info("✅ تم تشغيل Whisper بنجاح")
                    
            except Exception as e:
                error_msg = f"❌ خطأ أثناء تشغيل Whisper: {e}"
                logger.error(error_msg)
                logger.error(traceback.format_exc())
                self.error.emit(error_msg)
                return
            finally:
                # تنظيف العملية
                if self.whisper_proc:
                    try:
                        if self.whisper_proc.poll() is None:
                            self.whisper_proc.terminate()
                    except:
                        pass
                    self.whisper_proc = None
                
            self.progress.emit(70, 0, "تحويل الصوت إلى نص")
            
            if not os.path.exists(whisper_txt):
                error_msg = f"❌ ملف النص غير موجود بعد تنفيذ Whisper: {whisper_txt}"
                logger.error(error_msg)
                self.error.emit(error_msg)
                return

            # قراءة النص المستخرج واستخدام اللغة المختارة
            with open(whisper_txt, "r", encoding="utf-8") as f:
                transcript = f.read()
            detected_language = self.source_language if self.source_language else "unknown"
            self.language_detected.emit(detected_language)
            
            logger.info(f"📝 النص المستخرج ({len(transcript)} حرف): {transcript[:100]}...")
            self.model_loading.emit("")
            self.transcript_ready.emit(transcript)

            # 3. الترجمة من اللغة المختارة إلى اللغة المستهدفة
            logger.info("🌐 بدء الترجمة...")
            self.progress.emit(75, 0, "الترجمة")
            
            try:
                # استخدام الترجمة العامة مع اللغة المكتشفة واللغة المستهدفة
                translation = translate_text_general(transcript, detected_language, self.target_language)
                logger.info(f"🌐 النص المترجم ({len(translation)} حرف): {translation[:100]}...")
            except Exception as e:
                error_msg = f"❌ فشل في الترجمة: {e}"
                logger.error(error_msg)
                logger.error(traceback.format_exc())
                self.error.emit(error_msg)
                return
                
            self.progress.emit(80, 0, "الترجمة")
            
            if self._should_stop:
                logger.info("🛑 تم إيقاف المعالجة بعد الترجمة")
                self.stopped.emit()
                return

            # 4. توليد الصوت للغة المستهدفة
            logger.info("🔊 بدء توليد الصوت...")
            self.progress.emit(85, 0, "توليد الصوت")
            
            try:
                tts_start = time.time()
                # استخدام توليد الصوت الجديد مع اللغة المستهدفة
                success, audio_duration = asyncio.run(generate_audio_for_language(
                    translation, 
                    self.target_language, 
                    f"temp/audio_{self.target_language}.mp3", 
                    target_duration=duration,
                    voice_name=self.voice_name  # <--- استخدم المتغير الجديد
                ))
                tts_elapsed = time.time() - tts_start
                
                if not success:
                    error_msg = "❌ فشل في توليد الصوت"
                    logger.error(error_msg)
                    self.error.emit(error_msg)
                    return
                    
                logger.info(f"🔊 تم توليد الصوت بنجاح في {tts_elapsed:.2f} ثانية")
                if audio_duration:
                    logger.info(f"⏱️ مدة الصوت: {audio_duration:.2f} ثانية")
                    
            except Exception as e:
                error_msg = f"❌ فشل في توليد الصوت: {e}"
                logger.error(error_msg)
                logger.error(traceback.format_exc())
                self.error.emit(error_msg)
                return
                
            self.progress.emit(90, 0, "توليد الصوت")
            
            if self._should_stop:
                logger.info("🛑 تم إيقاف المعالجة بعد توليد الصوت")
                self.stopped.emit()
                return

            # 5. تمديد مدة الفيديو إذا لزم الأمر
            extended_video_path = None
            if audio_duration and duration and audio_duration > duration:
                logger.info("⏱️ تمديد مدة الفيديو...")
                self.progress.emit(92, 0, "تمديد مدة الفيديو")
                extended_video_path = os.path.join("temp", f"extended_{os.path.basename(self.video_path)}")
                if not extend_video_duration(self.video_path, audio_duration, extended_video_path):
                    error_msg = "❌ فشل في تمديد مدة الفيديو"
                    logger.error(error_msg)
                    self.error.emit(error_msg)
                    return
                video_to_merge = extended_video_path
                logger.info("✅ تم تمديد مدة الفيديو بنجاح")
            else:
                video_to_merge = self.video_path
                logger.info("✅ لا حاجة لتمديد مدة الفيديو")

            # 6. دمج الصوت مع الفيديو
            logger.info("🎬 بدء دمج الصوت مع الفيديو...")
            self.progress.emit(95, 0, "دمج الصوت مع الفيديو")
            
            # استخدام مسار الصوت المناسب للغة المستهدفة
            audio_file_path = f"temp/audio_{self.target_language}.mp3"
            
            if not merge_audio_with_video(video_to_merge, audio_file_path, final_video):
                error_msg = "❌ فشل في دمج الصوت مع الفيديو"
                logger.error(error_msg)
                self.error.emit(error_msg)
                return
                
            logger.info(f"✅ تم دمج الصوت مع الفيديو بنجاح: {final_video}")
            self.progress.emit(100, 0, "دمج الصوت مع الفيديو")
            
            if self._should_stop:
                logger.info("🛑 تم إيقاف المعالجة قبل الانتهاء")
                self.stopped.emit()
                return

            # حذف الفيديو الممتد المؤقت إذا تم إنشاؤه
            if extended_video_path and os.path.exists(extended_video_path):
                try:
                    os.remove(extended_video_path)
                    logger.info("🗑️ حذف الفيديو الممتد المؤقت")
                except Exception as e:
                    logger.warning(f"⚠️ فشل في حذف الفيديو الممتد المؤقت: {e}")

            self.final_video_path.emit(final_video)
            
            total_time = time.time() - self.start_time if hasattr(self, 'start_time') else 0
            success_msg = (
                "✅ تمت الدبلجة بنجاح!\n\n"
                f"عدد كلمات النص المستخرج: {len(transcript.split())}\n"
                f"مدة الفيديو: {(duration/60):.2f} min\n"
                f"زمن التنفيذ: {total_time:.2f} min\n\n"
                f"تم حفظ الفيديو في: {final_video}"
            )
            
            logger.info("🎉 تمت الدبلجة بنجاح!")
            self.success.emit(success_msg)
            
        except Exception as e:
            error_msg = f"❌ حدث خطأ أثناء المعالجة: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            self.error.emit(error_msg)
        finally:
            # تنظيف نهائي
            logger.info("🧹 تنظيف نهائي...")
            self.cleanup()
            # حذف جميع محتويات مجلد temp بعد الانتهاء
            try:
                temp_dir = os.path.join(os.getcwd(), "temp")
                if os.path.exists(temp_dir):
                    for filename in os.listdir(temp_dir):
                        file_path = os.path.join(temp_dir, filename)
                        if os.path.isfile(file_path) or os.path.islink(file_path):
                            os.unlink(file_path)
                        elif os.path.isdir(file_path):
                            shutil.rmtree(file_path)
                    logger.info("🧹 تم حذف جميع ملفات temp بنجاح")
            except Exception as e:
                logger.warning(f"⚠️ فشل في حذف ملفات temp: {e}")
            self.finished.emit()
            if self._should_stop:
                self.stopped.emit()

    def get_video_duration(self, video_path):
        try:
            ffmpeg_path = ensure_ffmpeg_available() or "ffmpeg"
            ffprobe_path = ffmpeg_path.replace("ffmpeg.exe", "ffprobe.exe") if ffmpeg_path.endswith("ffmpeg.exe") else "ffprobe"
            
            logger.info(f"🔧 استخدام ffprobe: {ffprobe_path}")
            
            result = subprocess.run([
                ffprobe_path, 
                "-v", "error", "-show_entries",
                "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", 
                video_path
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                duration = float(result.stdout.strip())
                logger.info(f"⏱️ مدة الفيديو: {duration:.2f} ثانية")
                return duration
            else:
                logger.error(f"❌ فشل في تحديد مدة الفيديو: {result.stderr}")
                return None
        except Exception as e:
            logger.error(f"❌ خطأ في تحديد مدة الفيديو: {e}")
            return None

class DubberApp(QWidget):
    """واجهة المستخدم الرئيسية مع تسجيل مفصل للأخطاء."""
    
    def __init__(self):
        super().__init__()
        logger.info("🚀 بدء إنشاء واجهة المستخدم...")
        
        try:
            self.setObjectName("mainWindow")
            self.setWindowTitle("Video Dubber AI - Multi-Language Dubbing")
            self.setGeometry(200, 200, 800, 600)
            self.setMinimumSize(700, 500)
            self.setWindowIcon(QIcon("video-dubber.ico"))
            self.showNormal()
            self.raise_()
            self.activateWindow()
            
            logger.info("✅ تم إعداد النافذة بنجاح")
            
            # إنشاء المجلدات المطلوبة
            self.create_required_directories()
            
            # فحص وتثبيت ffmpeg عند أول تشغيل
            self.check_ffmpeg_on_startup()
            
            self.init_ui()
            self.apply_styles()
            fade_in_widget(self)
            self.setWindowOpacity(1)
            self.show()
            self.setAcceptDrops(True)
            
            self.video_path = None
            self.final_video_path = None
            self.transcript = ""
            self.start_time = None
            self.end_time = None
            self.video_duration = None
            self.detected_language = None  # اللغة المكتشفة من الفيديو
            self.target_language = "ar"    # اللغة المستهدفة (العربية افتراضيًا)
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)
            self.progress_bar.setTextVisible(True)
            
            logger.info("✅ تم إنشاء واجهة المستخدم بنجاح")
            
        except Exception as e:
            logger.error(f"❌ خطأ في إنشاء واجهة المستخدم: {e}")
            logger.error(traceback.format_exc())
            raise

    def create_required_directories(self):
        """إنشاء المجلدات المطلوبة للبرنامج."""
        try:
            current_dir = os.getcwd()
            logger.info(f"📂 المسار الحالي: {current_dir}")
            
            required_dirs = ["temp", "output"]
            
            for dir_name in required_dirs:
                dir_path = os.path.join(current_dir, dir_name)
                try:
                    if not os.path.exists(dir_path):
                        os.makedirs(dir_path, exist_ok=True)
                        logger.info(f"✅ تم إنشاء مجلد: {dir_path}")
                    else:
                        logger.info(f"📁 مجلد موجود: {dir_path}")
                except Exception as e:
                    logger.error(f"❌ خطأ في إنشاء مجلد {dir_path}: {e}")
        except Exception as e:
            logger.error(f"❌ خطأ في إنشاء المجلدات: {e}")

    def check_ffmpeg_on_startup(self):
        """فحص وتثبيت ffmpeg عند بداية تشغيل التطبيق."""
        try:
            logger.info("🔧 فحص ffmpeg عند بداية التشغيل...")
            ffmpeg_path = ensure_ffmpeg_available()
            if ffmpeg_path:
                logger.info(f"✅ ffmpeg متاح في: {ffmpeg_path}")
            else:
                logger.warning("⚠️ تحذير: ffmpeg غير متاح، قد تواجه مشاكل في معالجة الفيديو")
        except Exception as e:
            logger.error(f"❌ خطأ في فحص ffmpeg: {e}")

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls and urls[0].toLocalFile().lower().endswith((".mp4", ".mov", ".avi", ".mkv", ".wmv", ".flv", ".webm")):
                event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            self.video_path = file_path
            self.label.setText(f"✅ Video selected: {os.path.basename(file_path)} (via drag & drop)")
            self.process_btn.setEnabled(True)
            logger.info(f"📁 تم اختيار الفيديو عبر السحب والإفلات: {file_path}")

    def init_ui(self):
        """تهيئة عناصر الواجهة الرسومية."""
        try:
            layout = QVBoxLayout()
            layout.setSpacing(20)
            layout.setContentsMargins(30, 30, 30, 30)

            # Header with modern title
            self.label = QLabel("🎬 Select a video to start dubbing")
            self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.label.setObjectName("headerLabel")

            # Language display section
            self.language_layout = QHBoxLayout()
            self.language_layout.setSpacing(20)

            # أنشئ القوائم المنسدلة للغات أولاً
            self.source_language_combo = QComboBox()
            self.source_language_combo.setObjectName("sourceLanguageCombo")
            self.source_language_combo.setMinimumWidth(200)
            self.source_language_combo.setToolTip("Select the original language of the video")

            self.target_language_combo = QComboBox()
            self.target_language_combo.setObjectName("targetLanguageCombo")
            self.target_language_combo.setMinimumWidth(200)
            self.target_language_combo.setToolTip("Select the dubbing target language")

            # ثم أضف اللغات والأعلام
            self.supported_languages = {
                "ar": "Arabic",
                "en": "English",
                "fr": "French",
                "es": "Spanish",
                "de": "German",
                "it": "Italian",
                "pt": "Portuguese",
                "ru": "Russian",
                "zh": "Chinese",
                "ja": "Japanese",
                "ko": "Korean",
                "hi": "Hindi",
                "tr": "Turkish",
                "nl": "Dutch",
                "pl": "Polish",
                "sv": "Swedish",
                "da": "Danish",
                "no": "Norwegian",
                "fi": "Finnish",
                "he": "Hebrew",
                "fa": "Persian",
                "ur": "Urdu",
                "bn": "Bengali",
                "th": "Thai",
                "vi": "Vietnamese",
                "id": "Indonesian",
                "ms": "Malay"
            }
            language_flags = {
                "ar": "🇸🇦", "en": "🇺🇸", "fr": "🇫🇷", "es": "🇪🇸", "de": "🇩🇪", "it": "🇮🇹", "pt": "🇵🇹", "ru": "🇷🇺", "zh": "🇨🇳", "ja": "🇯🇵", "ko": "🇰🇷", "hi": "🇮🇳", "tr": "🇹🇷", "nl": "🇳🇱", "pl": "🇵🇱", "sv": "🇸🇪", "da": "🇩🇰", "no": "🇳🇴", "fi": "🇫🇮", "he": "🇮🇱", "fa": "🇮🇷", "ur": "🇵🇰", "bn": "🇧🇩", "th": "🇹🇭", "vi": "🇻🇳", "id": "🇮🇩", "ms": "🇲🇾"
            }
            self.source_language_combo.clear()
            self.target_language_combo.clear()
            for code, name in self.supported_languages.items():
                flag = language_flags.get(code, "🌐")
                self.source_language_combo.addItem(f"{flag} {name}", code)
                self.target_language_combo.addItem(f"{flag} {name}", code)
            self.source_language_combo.setCurrentText("🇺🇸 English")
            self.target_language_combo.setCurrentText("🇸🇦 Arabic")

            # Arrow
            self.arrow_label = QLabel("➡️")
            self.arrow_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.arrow_label.setObjectName("arrowLabel")
            self.arrow_label.setStyleSheet("""
                QLabel {
                    color: white;
                    font-size: 20px;
                    font-weight: bold;
                }
            """)

            # Target language selection (right)
            self.target_language_combo = QComboBox()
            self.target_language_combo.setObjectName("targetLanguageCombo")
            self.target_language_combo.setMinimumWidth(200)
            self.target_language_combo.setToolTip("Select the dubbing target language")
            for code, name in self.supported_languages.items():
                self.target_language_combo.addItem(f"🌍 {name}", code)
            self.target_language_combo.setCurrentText("🌍 Arabic")

            # Voice selection dropdown
            self.voice_combo = QComboBox()
            self.voice_combo.setObjectName("voiceCombo")
            self.voice_combo.setStyleSheet(self.target_language_combo.styleSheet())
            self.voice_combo.setMinimumWidth(200)
            self.voice_combo.setToolTip("Select voice type (male/female)")

            self.language_layout.addWidget(self.source_language_combo)
            self.language_layout.addWidget(self.arrow_label)
            self.language_layout.addWidget(self.target_language_combo)
            self.language_layout.addWidget(self.voice_combo)

            # ربط تغيير اللغة المستهدفة
            self.target_language_combo.currentIndexChanged.connect(self.on_target_language_changed)

            # Modern text area with placeholder
            self.text_area = QTextEdit()
            self.text_area.setPlaceholderText("📝 The extracted transcript will appear here...")
            self.text_area.setReadOnly(True)
            self.text_area.setObjectName("transcriptArea")

            # Modern progress bar
            self.progress_bar = QProgressBar()
            self.progress_bar.setRange(0, 0)  # Indeterminate
            self.progress_bar.setVisible(False)
            self.progress_bar.setFixedHeight(35)
            self.progress_bar.setTextVisible(False)
            self.progress_bar.setObjectName("progressBar")

            # Modern buttons with unique IDs
            self.choose_btn = QPushButton("📁 Select Video")
            self.choose_btn.setObjectName("chooseBtn")
            self.process_btn = QPushButton("🚀 Start Dubbing")
            self.process_btn.setObjectName("processBtn")
            self.stop_btn = QPushButton("⏹️ Stop Processing")
            self.stop_btn.setObjectName("stopBtn")
            self.preview_btn = QPushButton("🎥 Open Video")
            self.preview_btn.setObjectName("previewBtn")
            self.preview_btn.setVisible(False)
            self.preview_btn.clicked.connect(self.preview_final_video)
            self.process_btn.setEnabled(False)
            self.stop_btn.setEnabled(False)

            # إضافة تأثير ظل للأزرار
            for btn in [self.choose_btn, self.process_btn, self.stop_btn, self.preview_btn]:
                shadow = QGraphicsDropShadowEffect(self)
                shadow.setBlurRadius(20)
                shadow.setXOffset(0)
                shadow.setYOffset(4)
                shadow.setColor(Qt.GlobalColor.black)
                btn.setGraphicsEffect(shadow)

            self.choose_btn.clicked.connect(self.choose_video)
            self.process_btn.clicked.connect(self.start_processing)
            self.stop_btn.clicked.connect(self.stop_processing)

            # Layout
            layout.addWidget(self.label)
            layout.addLayout(self.language_layout)
            layout.addWidget(self.text_area)
            layout.addWidget(self.progress_bar)
            button_layout = QHBoxLayout()
            button_layout.addWidget(self.choose_btn)
            button_layout.addWidget(self.process_btn)
            button_layout.addWidget(self.stop_btn)
            button_layout.addWidget(self.preview_btn)
            layout.addLayout(button_layout)
            self.setLayout(layout)
            logger.info("✅ تم إنشاء واجهة المستخدم بنجاح")
            # --- تحديث قائمة الأصوات عند بدء التشغيل ---
            self.update_voice_combo()
        except Exception as e:
            logger.error(f"❌ خطأ في إنشاء واجهة المستخدم: {e}")
            raise

    def update_voice_combo(self):
        """
        تحديث قائمة الأصوات المتاحة بناءً على اللغة المختارة.
        """
        try:
            lang_code = self.target_language_combo.currentData()
            voices = get_voices_for_language(lang_code)
            self.voice_combo.clear()
            for v in voices:
                self.voice_combo.addItem(f"{v['display']} [{v['gender']}]", v['name'])
            if self.voice_combo.count() > 0:
                self.voice_combo.setCurrentIndex(0)
        except Exception as e:
            logger.error(f"❌ خطأ في تحديث قائمة الأصوات: {e}")

    def choose_video(self):
        """اختيار ملف فيديو."""
        try:
            logger.info("📁 فتح نافذة اختيار الفيديو...")
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Select Video File",
                "",
                "Video Files (*.mp4 *.mov *.avi *.mkv *.wmv *.flv *.webm);;All Files (*)"
            )
            if file_path:
                self.video_path = file_path
                self.label.setText(f"✅ Video selected: {os.path.basename(file_path)}")
                self.process_btn.setEnabled(True)
                # لا تكتشف اللغة تلقائياً بعد الآن
            else:
                logger.info("❌ لم يتم اختيار أي ملف")
        except Exception as e:
            logger.error(f"❌ خطأ في اختيار الفيديو: {e}")

    def detect_video_language(self):
        """
        استخراج الصوت من الفيديو واكتشاف اللغة مباشرة من الصوت.
        """
        try:
            from core.audio_handler import extract_audio
            from core.audio_language import detect_audio_language
            from core.translator import get_language_name
            import os
            
            # إعادة تعيين اللغة المكتشفة
            self.detected_language = None
            
            # استخراج الصوت
            temp_audio = os.path.join("temp", "detect_lang_audio.wav")
            extract_audio(self.video_path, temp_audio)
            
            # اكتشاف اللغة من اسم الفيديو الأصلي أولاً
            video_filename = os.path.basename(self.video_path).lower()
            logger.info(f"🔍 فحص اسم الفيديو للكشف عن اللغة: {video_filename}")
            
            # كشف بسيط من اسم الفيديو
            if any(word in video_filename for word in ['arabic', 'ar', 'عربي']):
                lang_code = "ar"
            elif any(word in video_filename for word in ['english', 'en', 'eng']):
                lang_code = "en"
            elif any(word in video_filename for word in ['french', 'fr', 'francais']):
                lang_code = "fr"
            elif any(word in video_filename for word in ['spanish', 'es', 'espanol']):
                lang_code = "es"
            elif any(word in video_filename for word in ['german', 'de', 'deutsch']):
                lang_code = "de"
            elif any(word in video_filename for word in ['italian', 'it', 'italiano']):
                lang_code = "it"
            elif any(word in video_filename for word in ['portuguese', 'pt', 'portugues']):
                lang_code = "pt"
            elif any(word in video_filename for word in ['russian', 'ru', 'русский']):
                lang_code = "ru"
            elif any(word in video_filename for word in ['chinese', 'zh', '中文']):
                lang_code = "zh"
            elif any(word in video_filename for word in ['japanese', 'ja', '日本語']):
                lang_code = "ja"
            elif any(word in video_filename for word in ['korean', 'ko', '한국어']):
                lang_code = "ko"
            else:
                # إذا لم يتم العثور على كلمات في اسم الفيديو، استخدم الطريقة البسيطة
                lang_code = detect_audio_language(temp_audio)
            
            lang_name = get_language_name(lang_code)
            self.detected_language = lang_code
            self.source_language_label.setText(f"🌍 لغة الفيديو: {lang_name} ({lang_code})")
            logger.info(f"🌍 تم اكتشاف لغة الفيديو: {lang_name} ({lang_code})")
        except Exception as e:
            self.source_language_label.setText("🌍 لغة الفيديو: غير معروف")
            logger.error(f"❌ فشل في اكتشاف لغة الفيديو: {e}")

    def start_processing(self):
        """بدء معالجة الفيديو."""
        try:
            if not self.video_path:
                logger.warning("⚠️ لم يتم اختيار فيديو")
                return
            logger.info(f"🚀 بدء معالجة الفيديو: {self.video_path}")
            # الحصول على اللغة الأصلية المختارة
            source_language = self.source_language_combo.currentData()
            # الحصول على اللغة المستهدفة المختارة
            target_language = self.target_language_combo.currentData()
            target_language_name = self.supported_languages.get(target_language, target_language)
            logger.info(f"🌍 اللغة الأصلية: {source_language}, اللغة المستهدفة: {target_language_name} ({target_language})")
            # الحصول على الصوت المختار
            voice_name = self.voice_combo.currentData()
            # إنشاء خيط المعالجة مع تمرير اللغات والصوت
            self.worker = DebugPipelineWorker(self.video_path, target_language, voice_name=voice_name, source_language=source_language)
            self.worker.start_time = time.time()
            # ربط الإشارات
            self.worker.success.connect(self.show_success)
            self.worker.error.connect(self.show_error)
            self.worker.transcript_ready.connect(self.set_transcript)
            self.worker.finished.connect(self.on_worker_finished)
            self.worker.final_video_path.connect(self.set_final_video_path)
            self.worker.video_duration_ready.connect(self.set_video_duration)
            self.worker.model_loading.connect(self.on_model_loading)
            self.worker.stopped.connect(self.on_pipeline_stopped)
            self.worker.progress.connect(self.update_progress)
            self.worker.language_detected.connect(self.set_detected_language)
            # تحديث واجهة المستخدم
            self.process_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)
            self.text_area.clear()
            # بدء المعالجة
            self.worker.start()
            logger.info("✅ تم بدء خيط المعالجة")
        except Exception as e:
            logger.error(f"❌ خطأ في بدء المعالجة: {e}")
            logger.error(traceback.format_exc())

    def stop_processing(self):
        """إيقاف معالجة الفيديو."""
        try:
            logger.info("🛑 طلب إيقاف المعالجة...")
            if hasattr(self, 'worker') and self.worker:
                self.worker.stop()
            self.process_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.progress_bar.setVisible(False)
            logger.info("✅ تم إيقاف المعالجة")
        except Exception as e:
            logger.error(f"❌ خطأ في إيقاف المعالجة: {e}")

    def on_worker_finished(self):
        """عند انتهاء خيط المعالجة."""
        try:
            logger.info("✅ انتهى خيط المعالجة")
            self.process_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.progress_bar.setVisible(False)
        except Exception as e:
            logger.error(f"❌ خطأ في معالجة انتهاء الخيط: {e}")

    def set_final_video_path(self, path):
        """تعيين مسار الفيديو النهائي."""
        try:
            self.final_video_path = path
            self.preview_btn.setVisible(True)
            logger.info(f"📁 مسار الفيديو النهائي: {path}")
        except Exception as e:
            logger.error(f"❌ خطأ في تعيين مسار الفيديو: {e}")

    def set_transcript(self, text):
        """تعيين النص المستخرج."""
        try:
            self.transcript = text
            self.text_area.setText(text)
            logger.info(f"📝 تم تعيين النص المستخرج ({len(text)} حرف)")
        except Exception as e:
            logger.error(f"❌ خطأ في تعيين النص: {e}")

    def set_video_duration(self, duration):
        """تعيين مدة الفيديو."""
        try:
            self.video_duration = duration
            logger.info(f"⏱️ مدة الفيديو: {duration:.2f} ثانية")
        except Exception as e:
            logger.error(f"❌ خطأ في تعيين مدة الفيديو: {e}")

    def show_success(self, message):
        """عرض رسالة النجاح."""
        try:
            logger.info("✅ عرض رسالة النجاح")
            QMessageBox.information(self, "Success", message)
        except Exception as e:
            logger.error(f"❌ خطأ في عرض رسالة النجاح: {e}")

    def show_error(self, message):
        """عرض رسالة الخطأ."""
        try:
            logger.error(f"❌ عرض رسالة الخطأ: {message}")
            QMessageBox.critical(self, "Error", message)
        except Exception as e:
            logger.error(f"❌ خطأ في عرض رسالة الخطأ: {e}")

    def preview_final_video(self):
        """معاينة الفيديو النهائي."""
        try:
            if self.final_video_path and os.path.exists(self.final_video_path):
                logger.info(f"🎥 فتح الفيديو النهائي: {self.final_video_path}")
                os.startfile(self.final_video_path)
            else:
                logger.warning("⚠️ ملف الفيديو النهائي غير موجود")
        except Exception as e:
            logger.error(f"❌ خطأ في فتح الفيديو: {e}")

    def on_model_loading(self, msg):
        """عند تحميل النموذج."""
        try:
            if msg:
                self.label.setText(msg)
                logger.info(f"📥 تحميل النموذج: {msg}")
            else:
                self.label.setText("🎬 Select a video to start dubbing")
        except Exception as e:
            logger.error(f"❌ خطأ في معالجة تحميل النموذج: {e}")

    def on_pipeline_stopped(self):
        """عند إيقاف خط المعالجة."""
        try:
            logger.info("🛑 تم إيقاف خط المعالجة")
            self.label.setText("🛑 Processing stopped")
            self.process_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.progress_bar.setVisible(False)
        except Exception as e:
            logger.error(f"❌ خطأ في معالجة إيقاف المعالجة: {e}")

    def on_pipeline_finished(self):
        """عند انتهاء خط المعالجة."""
        try:
            logger.info("✅ انتهى خط المعالجة")
            self.label.setText("🎬 Select a video to start dubbing")
        except Exception as e:
            logger.error(f"❌ خطأ في معالجة انتهاء المعالجة: {e}")

    def update_progress(self, percent, eta_min, stage):
        """تحديث شريط التقدم."""
        try:
            self.progress_bar.setValue(percent)
            if eta_min > 0:
                self.progress_bar.setFormat(f"{stage} - {eta_min:.1f} min remaining")
            else:
                self.progress_bar.setFormat(stage)
            logger.debug(f"📊 التقدم: {percent}% - {stage}")
        except Exception as e:
            logger.error(f"❌ خطأ في تحديث التقدم: {e}")

    def set_detected_language(self, language_code):
        """تعيين اللغة المكتشفة من الفيديو."""
        try:
            self.detected_language = language_code
            language_name = get_language_name(language_code)
            self.source_language_label.setText(f"🌍 لغة الفيديو: {language_name}")
            logger.info(f"🌍 اللغة المكتشفة: {language_name} ({language_code})")
        except Exception as e:
            logger.error(f"❌ خطأ في تعيين اللغة المكتشفة: {e}")

    def on_target_language_changed(self):
        """عند تغيير اللغة المستهدفة، حدث قائمة الأصوات."""
        self.update_voice_combo()
        selected_code = self.target_language_combo.currentData()
        self.target_language = selected_code
        selected_name = self.supported_languages.get(selected_code, selected_code)
        logger.info(f"🌍 تم تغيير اللغة المستهدفة إلى: {selected_name} ({selected_code})")

    def closeEvent(self, event):
        """عند إغلاق النافذة."""
        try:
            logger.info("🚪 إغلاق التطبيق...")
            if hasattr(self, 'worker') and self.worker:
                self.worker.stop()
                self.worker.wait(5000)  # انتظار 5 ثوانٍ
            event.accept()
        except Exception as e:
            logger.error(f"❌ خطأ في إغلاق التطبيق: {e}")
            event.accept()

    def apply_styles(self):
        """
        تطبيق الأنماط على الواجهة.
        """
        try:
            style = """
            QWidget#mainWindow {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #667eea, stop:1 #764ba2);
                color: white;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QLabel#headerLabel {
                font-size: 24px;
                font-weight: bold;
                color: white;
                padding: 20px;
                background: rgba(255, 255, 255, 0.1);
                border-radius: 10px;
                margin: 10px;
            }
            QTextEdit#transcriptArea {
                background: rgba(255, 255, 255, 0.9);
                border: 2px solid rgba(255, 255, 255, 0.3);
                border-radius: 10px;
                padding: 15px;
                font-size: 14px;
                color: #333;
                selection-background-color: #667eea;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #667eea, stop:1 #764ba2);
                border: none;
                color: white;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 8px;
                min-width: 120px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #5a6fd8, stop:1 #6a4190);
                transform: translateY(-2px);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4a5fc8, stop:1 #5a3180);
            }
            QPushButton:disabled {
                background: #cccccc;
                color: #666666;
            }
            QProgressBar {
                border: 2px solid rgba(255, 255, 255, 0.3);
                border-radius: 10px;
                text-align: center;
                background: rgba(255, 255, 255, 0.1);
                color: white;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #667eea, stop:1 #764ba2);
                border-radius: 8px;
            }
            """
            self.setStyleSheet(style)
            # Style for language combo boxes
            combo_style = """
                QComboBox {
                    background: rgba(255, 255, 255, 0.2);
                    border-radius: 8px;
                    padding: 10px;
                    color: white;
                    font-weight: bold;
                    font-size: 14px;
                    border: 2px solid rgba(255, 255, 255, 0.3);
                }
                QComboBox::drop-down {
                    border: none;
                    width: 20px;
                }
                QComboBox::down-arrow {
                    image: none;
                    border-left: 5px solid transparent;
                    border-right: 5px solid transparent;
                    border-top: 5px solid white;
                }
                QComboBox QAbstractItemView {
                    background: rgba(255, 255, 255, 0.9);
                    color: #333;
                    border-radius: 8px;
                    selection-background-color: #667eea;
                }
            """
            self.source_language_combo.setStyleSheet(combo_style)
            self.target_language_combo.setStyleSheet(combo_style)
            logger.info("✅ تم تطبيق الأنماط بنجاح")
        except Exception as e:
            logger.error(f"❌ خطأ في تطبيق الأنماط: {e}")

def main():
    """الدالة الرئيسية للتطبيق."""
    try:
        logger.info("🚀 بدء تشغيل التطبيق...")
        app = QApplication(sys.argv)
        logger.info("✅ تم إنشاء تطبيق PyQt6 بنجاح")
        
        window = DubberApp()
        logger.info("✅ تم إنشاء نافذة التطبيق بنجاح")
        
        window.show()
        logger.info("✅ تم عرض النافذة بنجاح")
        
        logger.info("🔄 بدء حلقة الأحداث...")
        sys.exit(app.exec())
        
    except Exception as e:
        logger.error(f"❌ خطأ في تشغيل التطبيق: {str(e)}")
        logger.error(f"تفاصيل الخطأ: {traceback.format_exc()}")
        print(f"خطأ في تشغيل التطبيق: {str(e)}")
        print("راجع ملف debug_app.log للمزيد من التفاصيل")
        sys.exit(1)

if __name__ == "__main__":
    main() 