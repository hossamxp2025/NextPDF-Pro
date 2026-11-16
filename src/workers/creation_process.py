"""Qt-managed subprocess for Create PDF, with staged atomic publishing."""
import json
import logging
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from PySide6.QtCore import QObject, QProcess, Signal
from src.workers.ocr_process import OCRProcess

logger = logging.getLogger("NextPDF")


class CreationProcess(OCRProcess):
    """Run ``create_pdf`` in a child so a heavy document never freezes the UI."""

    progress = Signal(int, int)
    completed = Signal(str)
    failed = Signal(str)
    cancelled = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._temp = None
        self._target = None
        self._format = "pdf"
        self._cancelled = False
        self._buffer = b""

    def is_running(self):
        return self.process.state() != QProcess.NotRunning

    def start(self, sources, target):
        if self.is_running() or self._temp is not None:
            raise RuntimeError("A PDF creation job is already active")
        try:
            self._start_creation(sources, target)
        except Exception:
            logger.exception("Cannot prepare PDF creation job")
            self._cleanup()
            raise

    def _start_creation(self, sources, target):
        sources = [os.path.abspath(path) for path in sources]
        if not sources or not all(os.path.isfile(path) for path in sources):
            raise ValueError("No source files were selected")
        self._target = os.path.abspath(target)
        self._temp = tempfile.TemporaryDirectory(
            prefix=".nextpdf_create_", dir=str(Path(target).resolve().parent))
        self._directory = Path(self._temp.name)
        self._cancelled = False
        self._buffer = b""
        request = self._directory / "request.json"
        request.write_text(json.dumps({"sources": sources}), encoding="utf-8")
        self.process.setWorkingDirectory(str(Path(__file__).resolve().parents[2]))
        self.process.setProgram(sys.executable)
        self.process.setArguments((["--create-job"] if getattr(sys, "frozen", False)
                                   else ["-m", "src.creation_job"]) + [str(request)])
        self.process.start()

    def cancel(self):
        self._cancelled = True
        if self.is_running():
            if self.process.processId() <= 0:
                return
            if sys.platform == "win32":
                subprocess.run(["taskkill", "/PID", str(self.process.processId()), "/T", "/F"],
                               capture_output=True, timeout=10,
                               creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                self.process.kill()

    def _cancel_if_requested(self):
        if self._cancelled:
            self.cancel()

    def _read_progress(self):
        self._buffer += bytes(self.process.readAllStandardOutput())
        while b"\n" in self._buffer:
            line, self._buffer = self._buffer.split(b"\n", 1)
            try:
                data = json.loads(line)
                self.progress.emit(int(data["current"]), int(data["total"]))
            except (ValueError, KeyError, TypeError):
                logger.warning("Unexpected PDF creation progress record")

    def _process_error(self, error):
        if error == QProcess.FailedToStart:
            self._cleanup()
            self.failed.emit("Create PDF failed")

    def _finished(self, code, status):
        super()._finished(code, status)

    def _cleanup(self):
        super()._cleanup()
