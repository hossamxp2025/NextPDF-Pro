"""Capture native Qt diagnostic messages while reproducing a suite-order crash."""
import os
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import qInstallMessageHandler
import pytest

destination = ROOT / "docs/evidence/qt_native_messages.txt"
def record(kind, context, message):
    with destination.open("a", encoding="utf-8") as stream:
        stream.write(f"{kind}: {message}\n")
qInstallMessageHandler(record)
sys.exit(pytest.main(sys.argv[1:]))
