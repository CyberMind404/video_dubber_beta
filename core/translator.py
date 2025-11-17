import requests
import time
import re
import unicodedata
from langdetect import detect, DetectorFactory

API_KEY = "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"
DetectorFactory.seed = 0

def clean_arabic_text(text):
    """تنظيف النص العربي من الرموز الغريبة مع الاحتفاظ بالتشكيل الصحيح."""
    # إزالة الرموز الغريبة التي قد تظهر بسبب مشاكل الترميز
    unwanted_symbols = ['!', '@', '#', '$', '%', '^', '&', '*', '+', '=', '|', '\\', '/', '<', '>', '?', '`', '~']
    
    for symbol in unwanted_symbols:
        text = text.replace(symbol, '')
    
    # إزالة المسافات المتعددة
    text = re.sub(r'\s+', ' ', text)
    
    # تنظيف النص من الرموز غير المرغوبة في بداية ونهاية النص
    text = text.strip()
    
    return text

def split_text_smart(text, max_tokens=1500):
    """تقسيم النص الطويل إلى مقاطع ذكية مع الحفاظ على السياق."""
    # تقسيم النص إلى جمل باستخدام regex محسن
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks, current = [], ""
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
            
        # إذا كان الجملة الحالية + الجملة الجديدة أقل من الحد الأقصى
        if len(current) + len(sentence) < max_tokens:
            current += sentence + " "
        else:
            # حفظ المقطع الحالي إذا لم يكن فارغًا
            if current.strip():
                chunks.append(current.strip())
            current = sentence + " "
    
    # إضافة المقطع الأخير إذا لم يكن فارغًا
    if current.strip():
        chunks.append(current.strip())
    
    return chunks

def get_language_name(language_code: str) -> str:
    """الحصول على اسم اللغة من رمزها."""
    language_names = {
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
        "ko": "한국어",
        "hi": "हिन्दी",
        "tr": "Türkçe",
        "nl": "Nederlands",
        "pl": "Polski",
        "sv": "Svenska",
        "da": "Dansk",
        "no": "Norsk",
        "fi": "Suomi",
        "he": "עברית",
        "fa": "فارسی",
        "ur": "اردو",
        "bn": "বাংলা",
        "th": "ไทย",
        "vi": "Tiếng Việt",
        "id": "Bahasa Indonesia",
        "ms": "Bahasa Melayu",
        "auto": "اكتشاف تلقائي"
    }
    return language_names.get(language_code, language_code)

def translate_text_simple(text_en: str) -> str:
    """ترجمة نص إنجليزي إلى العربية باستخدام OpenRouter API - نسخة مبسطة."""
    return translate_text_general(text_en, "en", "ar")

def translate_text_general(text: str, source_language: str, target_language: str = "ar") -> str:
    """
    ترجمة نص من أي لغة إلى أي لغة أخرى باستخدام OpenRouter API.
    يجب تمرير اللغة المصدر بشكل صريح.
    """
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    # تقسيم النص إلى مقاطع أصغر إذا كان طويلاً
    max_length = 2000
    if len(text) > max_length:
        # تقسيم بسيط على الجمل
        sentences = re.split(r'(?<=[.!?])\s+', text)
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) < max_length:
                current_chunk += sentence + " "
            else:
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + " "
        
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
    else:
        chunks = [text]
    
    final_translation = ""
    
    # تحديد رسالة النظام بناءً على اللغات
    source_lang_name = get_language_name(source_language)
    target_lang_name = get_language_name(target_language)
    
    system_message = f"ترجم النص التالي من {source_lang_name} إلى {target_lang_name}، مع الحفاظ على جميع المصطلحات التقنية كما هي. اجعل الترجمة مقتضبة ومباشرة قدر الإمكان لتطابق طول النص الأصلي، وتجنب الإضافات غير الضرورية."
    
    # إضافة تعليمات خاصة للعربية
    if target_language == "ar":
        system_message += " أضف التشكيل الكامل (الحركات) إلى جميع الكلمات العربية في الترجمة لتسهيل القراءة الآلية."
    
    print(f"📝 ترجمة النص من {source_lang_name} إلى {target_lang_name} مقسم إلى {len(chunks)} جزء...")
    
    for i, chunk in enumerate(chunks):
        print(f"📝 ترجمة الجزء {i + 1} من {len(chunks)}...")
        
        data = {
            "model": "deepseek/deepseek-chat-v3-0324:free",
            "messages": [
                {
                    "role": "system",
                    "content": system_message
                },
                {
                    "role": "user",
                    "content": chunk
                }
            ]
        }
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            print("RESPONSE STATUS:", response.status_code)
            
            if response.status_code != 200:
                print("RESPONSE TEXT:", response.text)
                raise Exception(f"API returned status {response.status_code}")
                
            translated_chunk = response.json()["choices"][0]["message"]["content"].strip()
            
            # تنظيف النص من الرموز الغريبة مع الاحتفاظ بالتشكيل للعربية
            if target_language == "ar":
                translated_chunk = clean_arabic_text(translated_chunk)
            
            # إضافة الترجمة مع مسافة واحدة فقط
            if final_translation:
                final_translation += " " + translated_chunk
            else:
                final_translation = translated_chunk
                
            # انتظار قصير بين الطلبات لتجنب الحظر
            if i < len(chunks) - 1:
                time.sleep(1)
                
        except Exception as e:
            print(f"❌ خطأ أثناء ترجمة الجزء {i + 1}: {e}")
            # إضافة علامة للجزء الفاشل
            if final_translation:
                final_translation += f" [فشل في ترجمة الجزء {i + 1}]"
            else:
                final_translation = f"[فشل في ترجمة الجزء {i + 1}]"
    
    return final_translation.strip()

def detect_language_from_text(text: str) -> str:
    """
    اكتشاف لغة النص باستخدام langdetect.
    """
    try:
        lang = detect(text)
        return lang
    except Exception:
        return "unknown"
