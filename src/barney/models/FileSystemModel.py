from __future__ import annotations

import logging
from itertools import count, takewhile
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd
from qtpy.QtCore import QModelIndex, Signal, Slot
from qtpy.QtWidgets import QFileSystemModel

from barney.Utilities.parsers import parsePhraselist

from .DataFrameInterface import DataFrameInterface

if TYPE_CHECKING:
    from typing import Dict, List, Optional

    from .model import MainModel

logger = logging.getLogger(__name__)


class FileSystemModel(QFileSystemModel, DataFrameInterface):

    directoryLoadFinished = Signal()

    def __init__(self, parent: MainModel) -> None:
        DataFrameInterface.__init__(self)
        QFileSystemModel.__init__(self, parent)
        self.setOptions(QFileSystemModel.DontWatchForChanges)
        self.directoryLoaded.connect(self.addDirectory)
        self.getLocalFilepath = parent.pathMapper.getLocalFilepath
        self.currentDirectory = ""
        self.rowsInserted.connect(self.filesRead)
        self.mainModel = parent

    @Slot(QModelIndex, int, int)
    def filesRead(self, parent: QModelIndex, start: int, end: int) -> None:
        files: List[Path] = []
        for row in range(start, end + 1):
            childIndex = parent.child(row, 0)
            if not childIndex.isValid():
                continue
            fileInfo = self.fileInfo(childIndex)
            if fileInfo.isDir():
                continue
            strPath = fileInfo.absoluteFilePath()
            pathPath = Path(strPath)
            files.append(pathPath)
        self.addEntries(files, self.mainModel.pathMapper.getNetworkFilepath)

    @Slot(str)
    def addDirectory(self, path: str) -> None:
        logger.debug(f"FileSystemModel.addDirectory called for {path}")
        self.currentDirectory = path
        phraselistContents: Dict[str, str] = {}
        parent = self.index(path)
        nChildren = self.rowCount(parent)
        for i in range(nChildren):
            childIndex = parent.child(i, 0)
            fileInfo = self.fileInfo(childIndex)
            if fileInfo.fileName() == "phraselist.txt":
                phraselistContents = parsePhraselist(Path(fileInfo.absoluteFilePath()))
                break
        logger.debug(
            "FileSystemModel.addDirectory finished scanning for phraselist files"
        )
        if phraselistContents:
            try:
                firstPass = {
                    self.getLocalFilepath(Path(path)): transcription
                    for path, transcription in phraselistContents.items()
                }
                phraselistContents = {
                    localPath.as_posix(): transcription
                    for localPath, transcription in firstPass.items()
                    if localPath is not None
                }
            except AttributeError:
                logger.error(f"Is the phraselist {path} empty?")
                return None
            phraselistDataFrame = DataFrameInterface.phraselistToDataFrame(
                phraselistContents
            )
            self.mergePhraselistContents(phraselistContents, phraselistDataFrame)
            logger.debug(
                "FileSystemModel.addDirectory finished merging phraselist data"
            )
        self.updateAudiotags()
        logger.debug("FileSystemModel.addDirectory finished with updateAudiotags")
        localPaths = (
            self.getLocalFilepath(Path(path)) for path in self.audiotagData.keys()
        )
        logger.debug(
            "FileSystemModel.addDirectory finished converting audiotag paths to local paths"
        )
        for localPath in localPaths:
            if localPath is None:
                continue
            index = self.index(localPath.as_posix())
            if not index.isValid():
                logger.debug(
                    f"Trying to skip audiotag file {localPath} which isn't present"
                )
                continue
            # TODO: this logic is duplicated in AudiotagInterface
            # difference is there it runs when loading audiotag
            # this runs when loading directory
            # consider consolodating
            # self.dataChanged.emit(index, index)
        logger.debug(
            "FileSystemModel.addDirectory finished running through useless loop"
        )
        logger.debug("FileSystemModel.directoryLoadFinished about to be emitted...")
        self.directoryLoadFinished.emit()
        return None

    def currentSelection(self, index: QModelIndex) -> pd.Series:
        filepath = self.fileInfo(index).absoluteFilePath()
        row = self.df.loc[self.df["filepath"] == filepath]
        if row.empty:
            row
        else:
            return row.iloc[0]

    def currentSourceData(self, index: QModelIndex) -> Optional[Dict[str, str]]:
        if not index.isValid() or index.model() is not self:
            logger.warning("Current Source Data is invalid")
            return None
        row = self.currentSelection(index)
        if row is None:
            return None
        return self.sourceData[row.get("key")]

    def setRootPath(self, path: str) -> None:
        logger.debug(f"FileSystemModel got call to set root path to {path}")
        localPath = self.mainModel.pathMapper.getLocalFilepath(Path(path))
        logger.debug(f"FileSystemModel actually setting root path to {path}")
        if localPath is not None:
            super().setRootPath(localPath.as_posix())
            logger.debug("Finished setting root path as of superclass")
            self.addDirectory(path)

    def getChildPaths(self) -> List[str]:
        rowGenerator = (self.index(self.currentDirectory).child(y, 0) for y in count())
        return [
            self.filePath(index)
            for index in takewhile(lambda x: x.isValid(), rowGenerator)
            if not self.isDir(index)
        ]
