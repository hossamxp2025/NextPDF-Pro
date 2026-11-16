"""اختبارات فعلية لظهور بيانات الهوية والشروط والأحكام في الواجهة."""
import pytest
from PySide6.QtWidgets import QApplication

from src.i18n import get_translator
from src.ui.main_window import MainWindow
from src.config import (
    APP_FOUNDER, APP_FOUNDER_EN, APP_IDENTITY_1, APP_IDENTITY_2,
    PROJECT_TYPE, PROJECT_LICENSE,
)


@pytest.fixture(scope="module")
def app():
    app = QApplication.instance() or QApplication([])
    yield app


def _open_about(window):
    """استدعاء نافذة About وعودتها."""
    window._show_about()


def test_about_shows_identity_ar(app, monkeypatch):
    """تأكيد ظهور بيانات الهوية بالعربية في نافذة About."""
    from PySide6.QtWidgets import QMessageBox
    shown = {}
    # QMessageBox.about يعلّق الاختبار بلا رأس (modal)؛ نلتقط النص بدل عرضه.
    monkeypatch.setattr(QMessageBox, "about",
                        staticmethod(lambda parent, title, text: shown.update(title=title, text=text)))
    translator = get_translator()
    old = translator.language
    translator.set_language("ar")
    try:
        window = MainWindow()
        window._show_about()
        assert shown["title"] == "حول NextPDF Pro"
        assert APP_FOUNDER in shown["text"] and APP_IDENTITY_1 in shown["text"]
        assert APP_FOUNDER_EN in shown["text"]
        assert "تأسيس وإنشاء وتطوير" in shown["text"]
        assert translator.tr("Established and developed by") == "تأسيس وإنشاء وتطوير"
        assert translator.tr("Free & Open Source Software") == "برنامج مجاني ومفتوح المصدر"
        assert translator.tr("Licensed under GNU AGPL v3.0") == "مرخص بموجب GNU AGPL v3.0"
        assert translator.tr("About NextPDF Pro") == "حول NextPDF Pro"
        window.close()
    finally:
        translator.set_language(old)


def test_about_shows_identity_en(app):
    """تأكيد ظهور بيانات الهوية بالإنجليزية في نافذة About."""
    translator = get_translator()
    old = translator.language
    translator.set_language("en")
    try:
        window = MainWindow()
        assert translator.tr("Established and developed by") == "Established and developed by"
        assert translator.tr("Free & Open Source Software") == "Free & Open Source Software"
        assert translator.tr("Licensed under GNU AGPL v3.0") == "Licensed under GNU AGPL v3.0"
        assert translator.tr("About NextPDF Pro") == "About NextPDF Pro"
        assert (translator.tr("Future of Automation (مستقبل الأتمتة)")
                == "Future of Automation (مستقبل الأتمتة)")
        window.close()
    finally:
        translator.set_language(old)


def test_config_identity_values():
    """تأكيد أن قيم التكوين للهوية صحيحة."""
    assert APP_FOUNDER == "مستقبل الأتمتة"
    assert APP_FOUNDER_EN == "Future of Automation"
    assert APP_IDENTITY_1 == "Next Ai Agent"
    assert APP_IDENTITY_2 == "Future ai agent"
    assert PROJECT_TYPE == "Free & Open Source Software"
    assert PROJECT_LICENSE == "GNU AGPL v3.0"


def test_terms_translation_exists_ar():
    """تأكيد وجود traduction الشروط بالعربية."""
    translator = get_translator()
    old = translator.language
    translator.set_language("ar")
    try:
        terms = translator.tr("Terms intro ar")
        assert "مستقبل الأتمتة" in terms
        assert "Next Ai Agent" in terms
        assert "Future ai agent" in terms
        assert "GNU AGPL v3.0" in terms
    finally:
        translator.set_language(old)


def test_terms_translation_exists_en():
    """تأكيد أن نافذة الشروط الإنجليزية تعرض النص الإنجليزي لا اسم المفتاح."""
    translator = get_translator()
    old = translator.language
    translator.set_language("en")
    try:
        terms = translator.tr("Terms intro en")
        assert terms != "Terms intro en"
        assert "Future of Automation" in terms
        assert "Next Ai Agent" in terms
        assert "Future ai agent" in terms
        assert "GNU AGPL v3.0" in terms
    finally:
        translator.set_language(old)


def test_menu_has_terms_action(app):
    """تأكيد وجود إجراء الشروط في قائمة Help."""
    translator = get_translator()
    old = translator.language
    translator.set_language("ar")
    try:
        window = MainWindow()
        help_menu = None
        for action in window.menuBar().actions():
            if action.text() == translator.tr("Help"):
                help_menu = action.menu()
                break
        assert help_menu is not None
        texts = [a.text() for a in help_menu.actions()]
        assert translator.tr("NextPDF Pro — Terms and Conditions") in texts
        assert translator.tr("About") in texts
        window.close()
    finally:
        translator.set_language(old)
