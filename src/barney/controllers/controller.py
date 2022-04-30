from __future__ import annotations

import logging
from collections import defaultdict
from contextlib import suppress
from pathlib import Path
from typing import TYPE_CHECKING, DefaultDict, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
import sounddevice as sd
import soundfile as sf
from qtpy.QtCore import QAbstractTableModel, QModelIndex, QObject, Qt, Signal, Slot
from qtpy.QtWidgets import QFileSystemModel
from scipy.io.wavfile import read as wav_read
from signalworks.tracking import Wave

from .AudiotagInterface import AudioTagController
from .CacheController import CacheController
from .LineEditParser import LineEditParser
from .ParseManager import ParseManager
from .PlaybackController import PlaybackController
from .PlotController import PlotController

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ..models import MainModel
    from ..models.DatabaseModel import DatabaseModel
    from ..models.FileSystemModel import FileSystemModel
    from ..views.MainWindow import MainWindow


audioEncodings: DefaultDict[str, str] = defaultdict(lambda: "float64")
audioEncodings["PCM_S8"] = "int16"  # soundfile does not support int8
audioEncodings["PCM_U8"] = "int16"  # soundfile does not support uint16
audioEncodings["PCM_16"] = "int16"
audioEncodings["PCM_24"] = "int32"  # there is no np.int24
audioEncodings["PCM_32"] = "int32"
audioEncodings["FLOAT"] = "float32"
audioEncodings["DOUBLE"] = "float64"


class MainController(QObject):

    sigAcousticModelLoaded = Signal()
    sigSetFileName = Signal(str)
    sigStopRequested = Signal()
    sigPlayRequested = Signal(int, int)
    sigPlaybackPosition = Signal(int)
    sigSelectionFinished = Signal()
    sigShowTreeView = Signal()
    sigShowListView = Signal()

    def __init__(self, model: MainModel) -> None:
        super().__init__()
        self._model = model
        self.fileParser = ParseManager(self)
        # self.textCompleter = TextCompleter(
        #     self._model.fileProxyModel.completionModel, self
        # )
        self.lineParser = LineEditParser(self)
        self.audioTagController = AudioTagController(self)
        self.plotController = PlotController(self)
        self.playbackController = PlaybackController(self)
        self.cacheController = CacheController(self)

        self.mainWindow: MainWindow  # set in MainWindow.__init__

    # TODO: bulk of this should likely migrate to models
    @Slot(list)
    def addEntries(self, pathlist: List[Path]) -> None:
        logger.info(f"Controller received call to add {len(pathlist)} entries")
        networkPaths = [
            self._model.pathMapper.getNetworkFilepath(filepath) for filepath in pathlist
        ]
        self._model.fileProxyModel.beginResetModel()
        if self._model.fileProxyModel.sourceModel() is None:
            self._model.fileProxyModel.resetDatabaseModel()
        self._model.fileProxyModel.addEntries(
            [
                networkPath if networkPath is not None else localPath
                for (localPath, networkPath) in zip(pathlist, networkPaths)
            ]
        )
        self._model.fileProxyModel.endResetModel()

    @Slot(dict, pd.DataFrame)
    def loadDatabase(
        self, contents: Dict[str, Dict[str, str]], df: pd.DataFrame
    ) -> None:
        self._model.fileProxyModel.beginResetModel()
        self._model.fileProxyModel.resetDatabaseModel()
        self.mainWindow.listView.reset()
        self._model.fileProxyModel.sourceModel().loadDatabase(contents, df)
        self._model.fileProxyModel.endResetModel()

    def clearDatabase(self) -> None:
        logger.info("Controller received call to load database")
        self._model.fileProxyModel.beginResetModel()
        self._model.fileProxyModel.resetDatabaseModel()
        self._model.fileProxyModel.endResetModel()

    @Slot()
    def showTreeView(self) -> None:
        self.sigShowTreeView.emit()

    @Slot()
    def showListView(self) -> None:
        self._model.fileProxyModel.setSortRole(Qt.UserRole)
        self.sigShowListView.emit()

    @Slot(Path)
    def updateWorkingDirectory(self, workingDirectory: Path) -> None:
        self._model.currentWorkingDirectory = workingDirectory

    @Slot(dict, pd.DataFrame)
    def loadPhraselist(self, contents: Dict[str, str], df: pd.DataFrame) -> None:
        logger.info("loadPhraselist received call phraselist dict")
        self._model.fileProxyModel.sourceModel().mergePhraselistContents(contents, df)

    @Slot(QModelIndex)
    def selectIndex(self, modelIndex: QModelIndex) -> None:

        logger.debug(f"Selecting Index for {modelIndex.data()}")

        sourceModel: Union[FileSystemModel, DatabaseModel]
        if modelIndex.model() is self._model.fileProxyModel:
            sourceModel = modelIndex.model().sourceModel()
        else:
            sourceModel = modelIndex.model()
            modelIndex = self._model.fileProxyModel.mapFromSource(modelIndex)
        pathObj: Optional[Path]
        okToFail: bool
        if isinstance(sourceModel, QFileSystemModel):
            fileSystemIndex = modelIndex.model().mapToSource(modelIndex)
            pathObj = Path(sourceModel.fileInfo(fileSystemIndex).absoluteFilePath())
            okToFail = True
        elif isinstance(sourceModel, QAbstractTableModel):
            entryData = sourceModel.currentSelection(
                modelIndex.model().mapToSource(modelIndex)
            )
            pathObj = self._model.pathMapper.getLocalFilepath(
                Path(entryData["filepath"])
            )
            okToFail = False
        else:
            logger.error("Just what kind of model sent over this index?")
            pathObj = None
            okToFail = True
            raise RuntimeError
        self.sigStopRequested.emit()

        if pathObj is None or not pathObj.exists() or pathObj.is_dir():
            if isinstance(pathObj, Path) and pathObj.is_dir():
                logger.info(f"{pathObj.as_posix()} directory selected")
            else:
                logger.error(f"{pathObj} file selected, but not found")
            self.plotController.receiveNothing()
            self.sigSetFileName.emit("None")
            self._model.currentWaveform = None
        else:
            logger.debug(f"{pathObj.as_posix()} file selected")
            if okToFail:
                try:
                    track = self.getTrack(pathObj)
                except RuntimeError:
                    logger.info("File could not be loaded")
                    self.plotController.receiveNothing()
                    self.sigSetFileName.emit("None")
                    self._model.currentWaveform = None
                    return None
            else:
                track = self.getTrack(pathObj)
            self.plotController.receiveTrack(track)
            self.sigSetFileName.emit(pathObj.name)

            with suppress(sd.PortAudioError):
                self.playbackController.prepAudioStream()
        self.sigSelectionFinished.emit()

    def getTrack(self, pathObj: Path) -> Wave:
        if pathObj in self.cacheController.cacheBlacklist:
            logger.debug(f"Loading {pathObj} from file.")
            return self.load_audio(pathObj)

        logger.debug(f"Loading {pathObj} using cache.")
        return self.cacheController.getTrackCache(pathObj)

    def load_audio(self, pathObj: Path) -> Wave:
        methods = [_load_from_scipy, _load_from_soundfile]

        for method in methods:
            data = method(pathObj)
            if data is not None:
                fs, value = data
                break
        else:
            logger.error(f"Unable to open track {pathObj}")
            raise RuntimeError

        track = Wave(value, fs, path=pathObj)
        return track


def _load_from_soundfile(path: Path) -> Optional[Tuple[int, np.ndarray]]:
    logger.debug(f"Attempting to load {path.as_posix()} using soundfile")
    try:
        fileInfo = sf.info(path)
        value, fs = sf.read(
            path, dtype=audioEncodings[fileInfo.subtype], always_2d=True
        )
    except RuntimeError:
        logger.error(f"Soundfile was unable to open {path}")
        return None
    else:
        return fs, value


def _load_from_scipy(path: Path) -> Optional[Tuple[int, np.ndarray]]:
    logger.debug(f"Attempting to load {path.as_posix()} using scipy")
    try:
        fs, value = wav_read(path)
        if value.ndim == 1:
            value = value.reshape((value.shape[0], 1))
    except (RuntimeError, ValueError, UnboundLocalError):
        logger.error(f"Scipy was unable to open {path.as_posix()}")
        return None
    else:
        return fs, value
