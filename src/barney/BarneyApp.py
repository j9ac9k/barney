#! /usr/bin/env python3
import dataclasses
import logging
import re
import sys
from pathlib import Path
from timeit import default_timer as timer
from types import TracebackType
from typing import Any, List, Optional, Type, Union

from qtpy.QtCore import QMessageLogContext, Qt, Slot, qInstallMessageHandler
from qtpy.QtGui import QFont, QPalette
from qtpy.QtWidgets import QApplication, QStyleFactory

from barney.controllers import MainController
from barney.models import DarkThemeColors, LightThemeColors
from barney.models.LogHandler import QtLogHandler
from barney.models.model import MainModel
from barney.Utilities.ConfigClass import ConfigClass
from barney.views.BugDialog import Bug
from barney.views.LoggerDialog import LoggingDialog
from barney.views.MainWindow import MainWindow

from .__version__ import version

logger = logging.getLogger()
qtLogger = logging.getLogger("QMessageLog")
if __debug__:
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.WARN)


# console = logging.StreamHandler()
# console.setLevel(logging.DEBUG)
# formatter = logging.Formatter("%(name)-35s: %(levelname)-8s %(message)s")
# console.setFormatter(formatter)
# logger.addHandler(console)


@dataclasses.dataclass
class BarneySettings(ConfigClass):

    _lastDirectory: str = Path.home().as_posix()
    _lastFilter: str = "Database Files (*.db *.alignments *.tas *.errors)"
    _showLogEnergy: bool = False

    def __init__(self, config_key: str = "Barney Cached Parameters"):
        super().__init__(config_key)


class Barney:
    def __init__(self) -> None:
        logging.getLogger().setLevel(logging.DEBUG)

        start = timer()
        sys.argv.insert(0, "Barney")
        qInstallMessageHandler(self._log_handler)

        # handling hidpi
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
        if hasattr(QStyleFactory, "AA_UseHighDpiPixmaps"):
            QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
        self.qtapp = BarneyApp(sys.argv)

        sys.excepthook = self._excepthook
        finish = timer()
        logger.debug(
            f"Started Barney version {version} with a time of {finish-start:{0}.{3}} seconds"
        )

    @staticmethod
    def _log_handler(
        msg_type: int, msg_log_context: QMessageLogContext, msg_string: str
    ) -> None:
        if msg_type == 1:
            if re.match(
                "QGridLayoutEngine::addItem: Cell \\(\\d+, \\d+\\) " "already taken",
                msg_string,
            ):
                return None
            logger.warning(msg_string)
        elif msg_type == 2:
            qtLogger.critical(msg_string)
        elif msg_type == 3:
            qtLogger.error(msg_string)
        elif msg_type == 4:
            qtLogger.info(msg_string)
        elif msg_type == 0:
            qtLogger.debug(msg_string)
        else:
            qtLogger.warning(
                "received unknown message type from qt system "
                f"with contents {msg_string}"
            )

    @staticmethod
    def _excepthook(
        type_: Type[BaseException],
        value: BaseException,
        traceback: Optional[TracebackType],
    ) -> Any:
        logger.exception("Uncaught Exception", exc_info=(type_, value, traceback))

        if hasattr(QApplication.instance(), "mainView"):
            bug_box = Bug(
                QApplication.instance().mainView, type_, value, traceback
            )  # noqa: F821
            bug_box.open()


class BarneyApp(QApplication):
    def __init__(self, args: List[str]) -> None:
        super().__init__(args)
        self.colors: Union[
            Type[LightThemeColors], Type[DarkThemeColors]
        ] = DarkThemeColors
        self.paletteChanged.connect(self.onPaletteChange)
        self.onPaletteChange(self.palette())
        self.setApplicationName("Barney")
        self.handler = QtLogHandler(self)
        logger.addHandler(self.handler)

        self.logView = LoggingDialog(self)
        self.handler.setReceiver(self.logView.updateEntries)

        self.infoFont = QFont("Courier")
        self.infoFont.setStyleHint(QFont.Monospace)
        self.settings = BarneySettings()

    def startBarney(self) -> None:
        self.model = MainModel()
        self.mainController = MainController(self.model)
        self.mainView = MainWindow(self.model, self.mainController)

        # Configure Logger
        self.mainView.show()

    @Slot(QPalette)
    def onPaletteChange(self, palette: QPalette) -> None:
        if palette.base().color() == "#FFFFFF":
            self.colors = LightThemeColors
        else:
            self.colors = DarkThemeColors
        return None
