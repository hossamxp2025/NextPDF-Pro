"""Version identity must not diverge across source and distribution metadata."""
from pathlib import Path
from src import config, version


def test_version_metadata_matches_canonical_module():
    text = (Path(__file__).resolve().parents[1] / "VERSION.txt").read_text(encoding="utf-8")
    assert config.APP_VERSION == version.APP_VERSION
    assert config.BUILD_ID == version.BUILD_ID
    assert f"Version: {version.APP_VERSION}" in text
    assert f"Build: {version.BUILD_ID}" in text


def test_generated_windows_and_text_metadata_are_current():
    import runpy
    module = runpy.run_path(str(Path(__file__).resolve().parents[1] / "build/generate_metadata.py"))
    module["generate"](check=True)
