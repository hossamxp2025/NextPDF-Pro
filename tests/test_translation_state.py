"""Translation state must be shared by the UI and configuration."""
from src import config, i18n


def test_config_and_i18n_share_language_state():
    original = i18n.get_translator().language
    try:
        config.set_translator_language("ar")
        assert config.get_translator() is i18n.get_translator()
        assert i18n.get_translator().language == "ar"
        config.set_translator_language("en")
        assert config.get_translator().language == "en"
    finally:
        i18n.set_translator_language(original)
