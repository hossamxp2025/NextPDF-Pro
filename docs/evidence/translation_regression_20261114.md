# Translation compatibility and regression check

- Added a shared translator bridge in `src/config.py`; it initializes from the saved language setting. The existing language toggle updates both the setting and the shared translator. The new state-sharing test passed in the full run.
- Reproduction before patch: `python -m pytest tests/test_translation_state.py -q` failed with missing `set_translator_language`.
- After patch: `QT_QPA_PLATFORM=offscreen .venv\Scripts\python.exe -m pytest tests -q` collected the suite, but returned **42 passed, 15 failed, 10 teardown errors**.
- The current `src/ui/main_window.py` is the older 1.0.2 implementation and lacks `_contexts`; this is incompatible with the existing acceptance suite and the per-document isolation previously reported. `src/i18n.py` also contains only a subset of the earlier translations. Translation compatibility is not full UI localization.
- The Arabic searchable OCR acceptance test still fails because its reversed layer is rejected. Do not ship as complete. The release binary was not built or modified.
