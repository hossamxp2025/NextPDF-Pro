#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Base Worker for background operations in NextPDF Pro
Provides thread-safe operations with progress reporting and cancellation support.
"""

import logging
from PySide6.QtCore import QThread, Signal, QObject

logger = logging.getLogger("NextPDF")


class WorkerSignals(QObject):
    """Signals for worker communication."""
    started = Signal()
    finished = Signal(object)
    error = Signal(str)
    progress = Signal(int, int)  # current, total
    message = Signal(str)
    cancelled = Signal()


class BaseWorker(QThread):
    """Base class for all background workers."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.signals = WorkerSignals()
        self._cancelled = False
    
    def cancel(self):
        """Request cancellation of the worker."""
        self._cancelled = True
    
    def is_cancelled(self) -> bool:
        """Check if cancellation was requested."""
        return self._cancelled
    
    def run(self):
        """Execute the worker. Override in subclasses."""
        self.signals.started.emit()
        try:
            self._run()
        except Exception as e:
            logger.error(f"Worker error: {e}")
            self.signals.error.emit(str(e))
        finally:
            if not self._cancelled:
                self.signals.finished.emit(None)
            else:
                self.signals.cancelled.emit()
    
    def _run(self):
        """Actual worker logic. Override in subclasses."""
        pass
    
    def _emit_progress(self, current: int, total: int):
        """Emit progress signal if not cancelled."""
        if not self._cancelled:
            self.signals.progress.emit(current, total)
    
    def _emit_message(self, message: str):
        """Emit message signal if not cancelled."""
        if not self._cancelled:
            self.signals.message.emit(message)