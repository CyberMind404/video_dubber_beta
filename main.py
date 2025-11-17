import sys
import traceback
import logging
from PyQt6.QtWidgets import QApplication
from ui.gui import DubberApp

# إعداد التسجيل المفصل
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app_debug.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

def main():
    try:
        logging.info("🚀 بدء تشغيل التطبيق (الواجهة الرئيسية)...")
        app = QApplication(sys.argv)
        logging.info("✅ تم إنشاء تطبيق PyQt6 بنجاح")
        
        # إنشاء نافذة التطبيق الرئيسية
        window = DubberApp()
        logging.info("✅ تم إنشاء نافذة التطبيق بنجاح")
        
        window.show()
        logging.info("✅ تم عرض النافذة بنجاح")
        
        logging.info("🔄 بدء حلقة الأحداث...")
        sys.exit(app.exec())
        
    except Exception as e:
        logging.error(f"❌ خطأ في تشغيل التطبيق: {str(e)}")
        logging.error(f"تفاصيل الخطأ: {traceback.format_exc()}")
        print(f"خطأ في تشغيل التطبيق: {str(e)}")
        print("راجع ملف app_debug.log للمزيد من التفاصيل")
        sys.exit(1)

if __name__ == "__main__":
    main()
