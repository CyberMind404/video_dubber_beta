import os
import logging

logger = logging.getLogger(__name__)

# SpeechBrain غير متوفر في النسخة الحالية
SPEECHBRAIN_AVAILABLE = False
logger.info("ℹ️ SpeechBrain غير متوفر، سيتم استخدام كشف اللغة البسيط")

def detect_audio_language(audio_path):
    """
    كشف لغة الصوت باستخدام الطريقة البسيطة.
    """
    if not os.path.exists(audio_path):
        logger.error(f"❌ ملف الصوت غير موجود: {audio_path}")
        return "unknown"
    
    logger.info(f"🔧 بدء كشف اللغة - الطريقة البسيطة")
    
    try:
        # استخدام الطريقة البسيطة
        return detect_language_simple(audio_path)
    except Exception as e:
        logger.error(f"❌ خطأ في كشف لغة الصوت: {e}")
        return "en"  # افتراضي

def detect_language_simple(audio_path):
    """
    كشف بسيط للغة بناءً على اسم الملف أو مساره.
    """
    try:
        filename = os.path.basename(audio_path).lower()
        logger.info(f"🔍 فحص اسم الملف للكشف عن اللغة: {filename}")
        
        # كشف بسيط بناءً على اسم الملف
        if any(word in filename for word in ['arabic', 'ar', 'عربي']):
            return "ar"
        elif any(word in filename for word in ['english', 'en', 'eng']):
            return "en"
        elif any(word in filename for word in ['french', 'fr', 'francais']):
            return "fr"
        elif any(word in filename for word in ['spanish', 'es', 'espanol']):
            return "es"
        elif any(word in filename for word in ['german', 'de', 'deutsch']):
            return "de"
        elif any(word in filename for word in ['italian', 'it', 'italiano']):
            return "it"
        elif any(word in filename for word in ['portuguese', 'pt', 'portugues']):
            return "pt"
        elif any(word in filename for word in ['russian', 'ru', 'русский']):
            return "ru"
        elif any(word in filename for word in ['chinese', 'zh', '中文']):
            return "zh"
        elif any(word in filename for word in ['japanese', 'ja', '日本語']):
            return "ja"
        elif any(word in filename for word in ['korean', 'ko', '한국어']):
            return "ko"
        else:
            # افتراضي - إنجليزي
            logger.info("🌍 استخدام اللغة الافتراضية: الإنجليزية")
            return "en"
            
    except Exception as e:
        logger.error(f"❌ خطأ في الكشف البسيط للغة: {e}")
        return "en"

def get_supported_languages():
    """
    قائمة اللغات المدعومة.
    """
    return {
        "ar": "العربية",
        "en": "English", 
        "fr": "Français",
        "es": "Español",
        "de": "Deutsch",
        "it": "Italiano",
        "pt": "Português",
        "ru": "Русский",
        "zh": "中文",
        "ja": "日本語",
        "ko": "한국어"
    } 