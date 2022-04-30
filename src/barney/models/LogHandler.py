from __future__ import annotations

import logging
from typing import Callable, Dict, List, Optional

from qtpy.QtCore import QObject, Qt, QThread, Signal


def currentThreadName() -> str:
    return QThread.currentThread().objectName()


class QtLogHandler(QObject, logging.Handler):

    old_factory = logging.getLogRecordFactory()
    signal = Signal(str, logging.LogRecord)

    def __init__(self, parent: QObject, slotFunc: Optional[Callable] = None) -> None:
        super().__init__(parent)
        # self.metaConnect = self.signal.connect(slotFunc, Qt.QueuedConnection)
        if slotFunc is not None:
            self.setReceiver(slotFunc)
        logging.setLogRecordFactory(self.record_factory)

    def record_factory(self, *args: List, **kwargs: Dict) -> logging.LogRecord:
        record = self.old_factory(*args, **kwargs)
        record.qThreadName = currentThreadName()  # type: ignore
        return record

    def emit(self, record: logging.LogRecord) -> None:
        msg = self.format(record)
        self.signal.emit(msg, record)

    def setReceiver(self, slotFunc: Callable) -> None:
        self.metaConnect = self.signal.connect(slotFunc, Qt.QueuedConnection)
