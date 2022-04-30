from __future__ import annotations

import logging
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Optional

import pandas as pd
from qtpy.QtCore import QUrl, Signal, Slot

from barney.models.DataFrameInterface import DataFrameInterface
from barney.Utilities.parsers import parseAudiotag, parseDatabase

from ..models import BarneyThread, BarneyThreadManager

if TYPE_CHECKING:
    from typing import List, Union

    from .controller import MainController

logger = logging.getLogger(__name__)

ATDB_NAME = "audiotagdb3"
AUDIO_FILE_SUFFIXES = ("wav", "au", "wa1", "wa2", "nis", "flac", "mp3")


class ImportWorker(BarneyThread):

    importDatabaseSignal = Signal(dict, pd.DataFrame)
    importAudiotagSignal = Signal(defaultdict)
    addEntriesSignal = Signal(list)
    sigQueryWorkingDir = Signal()
    sigSetWorkingDirectory = Signal(Path)
    sigShowTreeView = Signal()
    sigShowListView = Signal()

    db_suffixes = {".db", ".alignments", ".tas", ".errors"}
    audio_suffixes = set(map(lambda x: f".{x}", AUDIO_FILE_SUFFIXES))

    def __init__(self) -> None:
        super().__init__()
        self._audioTagPath: Optional[Path] = None
        self.forced: Optional[Callable[[Path], None]] = None

    @Slot(object)
    def update(self, path: Union[QUrl, Path]) -> None:
        self.path = path

    @property
    def path(self) -> Path:
        return self.__path

    @path.setter
    def path(self, path: Union[QUrl, Path]) -> None:
        if isinstance(path, QUrl):
            self.__path = Path(
                path.toDisplayString(QUrl.FormattingOptions(QUrl.PreferLocalFile))
            )
        elif isinstance(path, Path):
            self.__path = path
        else:
            raise TypeError("ImportWorker.path must be type Path or QUrl.")

    @property
    def audioTagPath(self) -> Path:
        if self._audioTagPath is None:
            raise RuntimeError("AudioTagPath set to None")
        return self._audioTagPath

    @audioTagPath.setter
    def audioTagPath(self, newPath: Path) -> None:
        self._audioTagPath = newPath
        if not newPath.exists():
            logger.warning(f"New audiotag path, {newPath}, does not exist.")

    @Slot()
    def processhook(self) -> None:  # previously ParseManager.receiveQUrl
        logger.info(f"ImportWorker attempting to load {self.path}")
        if self.forced is not None:
            f = self.forced
            self.forced = None
            logger.info(f"Forcing {self.path} to be loaded using {f.__name__}")
            f(self.path)
        else:
            if self.path.is_dir():
                logger.debug(f"Loading {self.path} as directory.")
                self.importDirectory(self.path)
            elif self.path.suffix in self.db_suffixes or self.path.name == "forced":
                logger.debug(f"Loading {self.path} as database.")
                self.importDatabase(self.path)
            else:
                logger.debug(f"Loading {self.path} as individual entry.")
                self.importEntry(self.path)
        self.importAudiotag()
        logger.info("Process hook finished")

    def importEntry(self, path: Path) -> None:
        self.sigShowListView.emit()
        self.audioTagPath = path.parent / ATDB_NAME
        self.addEntriesSignal.emit([path])

    def importDatabase(self, path: Path) -> None:
        self.sigShowListView.emit()
        self.audioTagPath = path.parent / ATDB_NAME
        self.sigSetWorkingDirectory.emit(path.parent)
        contents = parseDatabase(path)
        df = DataFrameInterface.contentsToDataFrame(contents)
        self.importDatabaseSignal.emit(contents, df)

    def importAudiotag(self) -> None:
        if self._audioTagPath is not None and self._audioTagPath.exists():
            logger.info(f"ImportWorker attempting to load {self._audioTagPath}")
            contents = parseAudiotag(self._audioTagPath)
            self.importAudiotagSignal.emit(contents)

    def importDirectory(self, path: Path) -> None:
        logger.debug("importDirectory method started")
        self.sigSetWorkingDirectory.emit(path)
        self.audioTagPath = path / ATDB_NAME
        self.sigShowTreeView.emit()
        logger.debug("importDirectory method finished")


class ParseManager(BarneyThreadManager):
    def __init__(self, mainController: MainController) -> None:
        super().__init__(ImportWorker(), parent=mainController)
        self.mainController = mainController
        self._connect()

    def _connect(self) -> None:
        self.thread.importDatabaseSignal.connect(self.mainController.loadDatabase)
        self.thread.importAudiotagSignal.connect(
            self.mainController._model.fileProxyModel.loadAudiotags
        )
        self.thread.addEntriesSignal.connect(self.mainController.addEntries)
        self.thread.sigSetWorkingDirectory.connect(
            self.mainController.updateWorkingDirectory
        )
        self.thread.sigShowTreeView.connect(self.mainController.showTreeView)
        self.thread.sigShowListView.connect(self.mainController.showListView)

    @staticmethod
    def formattedAudioFileTypes(prefix: str) -> List[str]:
        return [f"{prefix}.{typ}" for typ in AUDIO_FILE_SUFFIXES]

    @Slot(QUrl)
    def receiveQUrl(self, incomingUrl: QUrl) -> None:
        if isinstance(incomingUrl, Path):
            raise TypeError
        prettyPath = incomingUrl.toDisplayString(
            QUrl.FormattingOptions(QUrl.PreferLocalFile)
        )
        logger.info(
            f"ParseManager received signal to start ImportWorker thread with file {prettyPath}"
        )
        self.thread.path = incomingUrl
        self.run_thread()

    @Slot(QUrl, str)
    def receiveQUrlForced(self, incomingUrl: QUrl, forceAs: str) -> None:
        forcedMapping = {
            "database": self.thread.importDatabase,
            "audio": self.thread.importEntry,
        }
        self.thread.path = incomingUrl

        if forceAs in forcedMapping.keys():
            self.thread.forced = forcedMapping[forceAs]
        else:
            logger.warning(
                f"Received force as signal not matching known entries: {forceAs}"
            )
        self.run_thread()
