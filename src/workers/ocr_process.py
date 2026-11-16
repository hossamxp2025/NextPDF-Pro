"""Qt-managed subprocess OCR with staged output and explicit cancellation."""
import json
import logging
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from PySide6.QtCore import QObject, QProcess, Signal
from src.job_result import read_result

logger = logging.getLogger("NextPDF")


class OCRProcess(QObject):
    formats = {"pdf", "txt"}
    module_name = "src.ocr_job"
    cli_flag = "--ocr-job"
    progress = Signal(int, int)
    completed = Signal(str)
    failed = Signal(str)
    cancelled = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.process = QProcess(self)
        self.process.readyReadStandardOutput.connect(self._read_progress)
        self.process.finished.connect(self._finished)
        self.process.errorOccurred.connect(self._process_error)
        self.process.started.connect(self._cancel_if_requested)
        self._temp = None
        self._cancelled = False
        self._buffer = b""

    def is_running(self):
        return self.process.state() != QProcess.NotRunning

    def start(self, pdf_bytes, target, language, pages, output_format):
        if self.is_running() or self._temp is not None:
            raise RuntimeError("OCR process is already active")
        try:
            self._start(pdf_bytes, target, language, pages, output_format)
        except Exception:
            logger.exception("Cannot prepare child job")
            self._cleanup()
            raise

    def _start(self, pdf_bytes, target, language, pages, output_format):
        if language not in {"ara", "eng", "ara+eng"} or output_format not in self.formats:
            raise ValueError("Invalid OCR options")
        self._target = os.path.abspath(target)
        # Stage on the destination filesystem so publishing is an atomic rename.
        self._temp = tempfile.TemporaryDirectory(prefix=".nextpdf_job_", dir=str(Path(target).resolve().parent))
        self._directory = Path(self._temp.name)
        self._format = output_format
        self._cancelled = False
        self._buffer = b""
        (self._directory / "input.pdf").write_bytes(pdf_bytes)
        request = self._directory / "request.json"
        request.write_text(json.dumps({"language": language, "pages": pages, "format": output_format}), encoding="utf-8")
        self.process.setWorkingDirectory(str(Path(__file__).resolve().parents[2]))
        self.process.setProgram(sys.executable)
        self.process.setArguments(([self.cli_flag] if getattr(sys, "frozen", False)
                                   else ["-m", self.module_name]) + [str(request)])
        self.process.start()

    def cancel(self):
        self._cancelled = True
        if self.is_running():
            if self.process.processId() <= 0:
                return
            if sys.platform == "win32":
                # PID is obtained from this QProcess, not from input or a PDF.
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
                logger.warning("Unexpected OCR progress record")

    def _process_error(self, error):
        logger.error("Child process error %s: %s", error, self.process.errorString())
        if error == QProcess.FailedToStart:
            self._cleanup()
            self.failed.emit("OCR failed")

    def _finished(self, code, status):
        self._read_progress()
        outcome, message = self.failed, "OCR failed"
        try:
            if self._cancelled:
                outcome, message = self.cancelled, None
            else:
                stderr = bytes(self.process.readAllStandardError()).decode("utf-8", "replace")
                trace_file = self._directory / "traceback.txt"
                if trace_file.is_file():
                    stderr += trace_file.read_text(encoding="utf-8")
                if stderr:
                    logger.error("Child diagnostics (exit %s): %s", code, stderr)
                result = read_result(self._directory)
                if code != 0 or status != QProcess.NormalExit or not result["ok"]:
                    message = result.get("error_code", "job_failed")
                    logger.error("Child failed: exit=%s status=%s result=%s", code, status, result)
                else:
                    self._publish_output()
                    outcome, message = self.completed, self._target
        except Exception:
            logger.exception("Invalid child result or cannot publish output")
        finally:
            self._cleanup()
        # Cleanup precedes signals: slots can immediately start another job.
        if message is None:
            outcome.emit()
        else:
            outcome.emit(message)

    def _publish_output(self):
        output = self._directory / ("output." + self._format)
        if not output.is_file() or output.stat().st_size == 0:
            raise ValueError("Missing output")
        if self._format == "xlsx":
            from openpyxl import load_workbook
            book = load_workbook(output, read_only=True)
            try:
                if not book.worksheets:
                    raise ValueError("Empty workbook")
            finally:
                book.close()
        os.replace(output, self._target)

    def _cleanup(self):
        if self._temp:
            temp, self._temp = self._temp, None
            try:
                temp.cleanup()
            except OSError:
                logger.exception("Cannot remove child temporary directory")


class ConversionProcess(OCRProcess):
    from src.engine.conversion import SUPPORTED as formats
    module_name = "src.conversion_job"
    cli_flag = "--conversion-job"
