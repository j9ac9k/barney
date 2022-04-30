from __future__ import annotations

import logging
from time import time  # , sleep

from qtpy.QtCore import QObject, QThread, Signal, Slot

logger = logging.getLogger(__name__)


class BarneyThread(QThread):
    # not an ABC, because monkey patching w/ processhook could be useful
    """Any multi-threading objects in Barney should derive from this class.
    The child class should override 'processhook' which will be called by
    'BarneyThread.run' in an Exception-safe block."""

    success = Signal()
    failure = Signal(BaseException)

    def __init__(self, parent: QObject = None) -> None:
        super().__init__(parent)
        self.name = type(self).__name__
        self.finished.connect(self._logDebugFinished)
        self.success.connect(self._logInfoFinishedSuccess)
        self.failure.connect(BarneyThreadManager.failure)

    def processhook(self) -> None:
        """Override this function to have it called in the separate thread"""
        raise NotImplementedError(f"{self.name} must provide a hook.")

    def run(self) -> None:
        """calls 'processhook' in an Exception-safe block. 'processhook'
        can not take any arguments, or return any values. Any data requirements
        should instead be handled using class members of a subclass that
        overrides 'processhook'."""

        ####  we add this so coverage can detect executed code
        import sys
        import threading

        sys.settrace(threading._trace_hook)  # type: ignore
        ####
        try:
            logger.debug(f"Running {self.name} on {QThread.currentThread()}")
            s = time()
            self.processhook()
            e = time()
            logger.info(f"{self.name}.processhook took {(e - s):.3f} s")
            self.success.emit()
        except BaseException as x:
            self.failure.emit(x)
            logger.error(f"{type(x).__name__} caught in {self.name}.run")

    def _logDebugFinished(self) -> None:
        logger.debug(f"{self.name} finished.")

    def _logInfoFinishedSuccess(self) -> None:
        logger.debug(f"{self.name} finished successfully")


class BarneyThreadManager(QObject):
    """Any classes in Barney that manages a child thread, should inherit
    from BarneyThreadManager, which receives/contains and manages a
    BarneyThread object."""

    def __init__(self, thread: BarneyThread, parent: QObject = None) -> None:
        QObject.__init__(self, parent=parent)
        self.name = type(self).__name__
        self.thread = thread

    @staticmethod
    @Slot(BaseException)
    def failure(e: BaseException) -> None:
        """receives exception via Signal from child thread
        and raises in current thread."""
        raise e

    def run_thread(self) -> None:
        logger.debug(f"Starting {self.thread.name}")
        self.thread.start()
