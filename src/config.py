import os
import sys
import json
import base64
from pathlib import Path

# Application metadata
APP_NAME = "NextPDF Pro"
from src.version import APP_VERSION, BUILD_ID
APP_ORGANIZATION = "مستقبل الأتمتة"
APP_DESCRIPTION = "Professional PDF Editor for Windows"
APP_FOUNDER = "مستقبل الأتمتة"
APP_FOUNDER_EN = "Future of Automation"
APP_IDENTITY_1 = "Next Ai Agent"
APP_IDENTITY_2 = "Future ai agent"
PROJECT_TYPE = "Free & Open Source Software"
PROJECT_LICENSE = "GNU AGPL v3.0"


def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Paths - use LOCALAPPDATA for writable user data (not APPDATA)
local_app_data = os.environ.get("LOCALAPPDATA")
if local_app_data:
    data_dir_base = Path(local_app_data)
else:
    data_dir_base = Path.home() / "AppData" / "Local"

# Project resource directories (read-only, embedded in EXE)
BASE_DIR = Path(__file__).resolve().parent.parent
RESOURCES_DIR = BASE_DIR / "resources"

# User data directories (writable, in LOCALAPPDATA)
DATA_DIR = data_dir_base / "NextPDF-Pro"
LOG_DIR = DATA_DIR / "logs"
ICONS_DIR = RESOURCES_DIR / "icons"
TRANSLATIONS_DIR = RESOURCES_DIR / "translations"
FONTS_DIR = RESOURCES_DIR / "fonts"
SETTINGS_FILE = DATA_DIR / "settings.json"
RECENT_FILES_FILE = DATA_DIR / "recent.json"
LOG_FILE = LOG_DIR / "nextpdf.log"

# Default settings
DEFAULT_SETTINGS = {
    "language": "ar",  # ar or en
    "theme": "light",  # light or dark
    "recent_files": [],
    "window_geometry": None,
    "window_state": None,
    "zoom_level": 100,
    "auto_save": True,
    "auto_save_interval": 300,  # seconds
    "render_dpi": 150,
    "cache_size": 500,  # MB
    "ocr_language": "ara+eng",
    "ocr_enabled": True,
}

# UI constants
MIN_ZOOM = 10
MAX_ZOOM = 800
ZOOM_STEP = 10

# PDF constants
DEFAULT_DPI = 72
PAGE_DISPLAY_MODES = ["single", "facing", "continuous"]

# Ribbon tabs
RIBBON_TABS = [
    "file", "home", "edit_pdf", "organize_pages", "convert",
    "ocr", "forms", "sign", "protect", "tools", "help"
]


# Simple translation system for Arabic/English
class SimpleTranslator:
    """Simple in-memory translation system for Arabic/English."""
    
    TRANSLATIONS = {
        "ar": {
            "NextPDF Pro": "NextPDF Pro",
            "Professional PDF Editor for Windows": "محرر PDF احترافي لنظام Windows",
            "File": "ملف",
            "Edit": "تحرير",
            "View": "عرض",
            "Tools": "أدوات",
            "Help": "مساعدة",
            "New": "جديد",
            "Open": "فتح",
            "Save": "حفظ",
            "Save As": "حفظ باسم",
            "Exit": "خروج",
            "Undo": "تراجع",
            "Redo": "إعادة",
            "Zoom In": "تكبير",
            "Zoom Out": "تصغير",
            "Fit Page": "تكيف الصفحة",
            "Fit Width": "تكيف العرض",
            "OCR": "التعرف الضوئي على الحروف",
            "About": "حول",
            "Ready": "جاهز",
            "Saved": "تم الحفظ",
            "No Selection": "لا يوجد تحديد",
            "Select an element to view its properties": "حدد عنصرًا من المستند لعرض خصائصه",
            "Pages": "الصفحات",
            "Text Properties": "خصائص النص",
            "Image Properties": "خصائص الصورة",
            "Font Family": "نوع الخط",
            "Font Size": "حجم الخط",
            "Color": "اللون",
            "Direction": "الاتجاه",
            "Style": "النمط",
            "Bold": "عريض",
            "Italic": "مائل",
            "Underline": "تحته خط",
            "Regular": "عادي",
            "LTR": "من اليسار إلى اليمين",
            "RTL": "من اليمين إلى اليسار",
            "Arabic": "العربية",
            "English": "الإنجليزية",
            "Position": "الموضع",
            "Rotation": "الدوران",
            "Opacity": "الشفافية",
            "Size": "الحجم",
            "Opened": "تم فتح",
            "Insert": "إدراج",
            "Organize": "تنظيم",
            "Review": "مراجعة",
            "Convert": "تحويل",
            "Protect": "حماية",
            "Sign": "توقيع",
            "Home": "الرئيسية",
            "Edit PDF": "تحرير PDF",
            "Organize Pages": "تنظيم الصفحات",
            "View": "عرض",
        },
        "en": {
            # English is the default, keys map to themselves
        },
    }
    
    def __init__(self, language_code="en"):
        self.language = language_code
    
    def tr(self, key):
        """Translate a key to the current language."""
        if self.language == "ar" and key in self.TRANSLATIONS["ar"]:
            return self.TRANSLATIONS["ar"][key]
        return key
    
    def set_language(self, language_code):
        self.language = language_code


def get_translator():
    """Get the global translator instance."""
    from src.i18n import get_translator as shared_translator
    return shared_translator()


def set_translator_language(language):
    """Update the shared translator used by the window and viewer."""
    from src.i18n import set_translator_language as set_shared_language
    return set_shared_language(language)

# Ensure directories exist
def ensure_dirs():
    for d in [DATA_DIR, LOG_DIR, RESOURCES_DIR, ICONS_DIR, TRANSLATIONS_DIR, FONTS_DIR]:
        try:
            d.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

# Settings management
class Settings:
    def __init__(self):
        ensure_dirs()
        self._data = dict(DEFAULT_SETTINGS)
        self.load()

    def _serialize_value(self, value):
        """Convert a value to JSON-serializable format."""
        from PySide6.QtCore import QByteArray
        if isinstance(value, QByteArray):
            return {"__type__": "QByteArray", "data": base64.b64encode(bytes(value)).decode("ascii")}
        return value

    def _deserialize_value(self, value):
        """Convert a JSON value back to its original type."""
        from PySide6.QtCore import QByteArray
        if isinstance(value, dict) and value.get("__type__") == "QByteArray":
            return QByteArray.fromBase64(value["data"].encode("ascii"))
        return value

    def load(self):
        try:
            if SETTINGS_FILE.exists():
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                for key, val in loaded.items():
                    self._data[key] = self._deserialize_value(val)
        except Exception:
            pass

    def save(self):
        try:
            serializable = {}
            for key, val in self._data.items():
                serializable[key] = self._serialize_value(val)
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(serializable, f, ensure_ascii=False, indent=2)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to save settings: {e}")

    def get(self, key, default=None):
        return self._data.get(key, default)

    def set(self, key, value):
        self._data[key] = value
        self.save()

settings = Settings()

# Global translator instance (must be after settings instance)
set_translator_language(settings.get("language", "ar"))
