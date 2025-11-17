import whisper
import os
from pathlib import Path

def is_whisper_model_downloaded(model_name: str) -> bool:
    # Whisper downloads models to ~/.cache/whisper or WHISPER_CACHE_DIR
    cache_dir = os.environ.get("WHISPER_CACHE_DIR") or os.path.join(Path.home(), ".cache", "whisper")
    model_file = os.path.join(cache_dir, f"{model_name}.pt")
    return os.path.exists(model_file)

def detect_language(audio_path: str, model_name: str = "medium") -> str:
    """اكتشاف لغة الفيديو تلقائيًا باستخدام Whisper."""
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"الملف الصوتي غير موجود: {audio_path}")
    
    print(f"🔍 اكتشاف لغة الفيديو: {audio_path}")
    model = whisper.load_model(model_name)
    result = model.transcribe(audio_path, task="transcribe")
    
    # الحصول على اللغة المكتشفة
    detected_language = result.get("language", "unknown")
    print(f"✅ اللغة المكتشفة: {detected_language}")
    
    return detected_language

def transcribe_audio(audio_path: str, model_name: str = "medium", should_stop: bool = False) -> str:
    """تحويل ملف صوتي إلى نص باستخدام نموذج Whisper المحدد."""
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"الملف الصوتي غير موجود: {audio_path}")
    print(f"🧠 يتم الآن تحويل الصوت إلى نص من الملف: {audio_path} (model={model_name})")
    model = whisper.load_model(model_name)
    result = model.transcribe(audio_path)
    return result.get("text", "")

def transcribe_with_language_detection(audio_path: str, model_name: str = "medium") -> tuple:
    """تحويل الصوت إلى نص مع اكتشاف اللغة في نفس الوقت."""
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"الملف الصوتي غير موجود: {audio_path}")
    
    print(f"🧠 تحويل الصوت إلى نص مع اكتشاف اللغة: {audio_path}")
    model = whisper.load_model(model_name)
    result = model.transcribe(audio_path)
    
    text = result.get("text", "")
    language = result.get("language", "unknown")
    
    print(f"✅ النص المستخرج: {len(text)} حرف")
    print(f"✅ اللغة المكتشفة: {language}")
    
    return text, language
