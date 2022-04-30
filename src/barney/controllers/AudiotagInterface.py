from __future__ import annotations

import logging
import os
import sqlite3
from contextlib import suppress
from pathlib import Path
from typing import TYPE_CHECKING

from qtpy.QtCore import QModelIndex, QObject, QThread, Signal, Slot
from qtpy.QtWidgets import QApplication

from ..Utilities.parsers import makeAudiotagEntry

if TYPE_CHECKING:
    from typing import Callable, Dict, List, Optional, Tuple

    from barney.Utilities.parsers import AudiotagEntry

    from .controller import MainController


logger = logging.getLogger(__name__)


class AudiotagCommunicationThread(QThread):

    sigAddFinished = Signal(object)
    sigRemoveFinished = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self.audioTagPath: Optional[Path] = None

    @Slot(object)
    def setAudiotagPath(self, audioTagPath: Path) -> None:
        self.audioTagPath = audioTagPath

    def run(self) -> None:
        pass

    @Slot(object, object, object)
    def writeToDatabase(
        self, pairs: Dict[str, QModelIndex], data: Dict[str, str], tagtype: str
    ) -> None:
        if self.audioTagPath is None:
            logger.error("No Audiotag Path set")
            return None
        returnedData = []
        conn = sqlite3.connect(self.audioTagPath.as_posix())
        c = conn.cursor()
        create_table_query = """
        CREATE TABLE IF NOT EXISTS tagTable (
        tagType TEXT NOT NULL,
        audioFile TEXT NOT NULL,
        reason TEXT NULL,
        tagger TEXT NULL,
        comment TEXT NULL,
        timestamp TEXT NULL
        );
        """
        try:
            c.execute(create_table_query)
            for filepath, index in pairs.items():
                entry = makeAudiotagEntry(filepath, tagtype, data)
                returnedData.append((entry, index))
                query = f"""
                DELETE FROM tagTable
                WHERE tagType = '{entry.tagType}' AND audioFile = '{entry.audioFile}';
                """
                c.execute(query)
                query = f"""
                INSERT INTO tagTable {entry._fields}
                VALUES ('{entry.tagType}',
                        '{entry.audioFile}',
                        '{entry.reason}',
                        '{entry.tagger}',
                        '{entry.comment}',
                        {entry.timestamp})
                """
                logger.debug(f"query = {query}")
                c.execute(query)
            conn.commit()
        except sqlite3.OperationalError:
            logger.error("Fatal error when executing SQL")
            return None
        finally:
            c.close()
            conn.close()
        with suppress(OSError):
            os.chmod(self.audioTagPath, 0o664)

        self.sigAddFinished.emit(returnedData)

    @Slot(object, object)
    def removeFromDatabase(self, pairs: Dict[str, QModelIndex], tagType: str) -> None:
        if self.audioTagPath is None:
            logger.error("No Audiotag Path set")
            return None
        returnedData = []
        conn = sqlite3.connect(self.audioTagPath)
        c = conn.cursor()
        try:
            for filepath, index in pairs.items():
                returnedData.append((tagType, filepath, index))
                query = f"""
                DELETE
                FROM tagTable
                WHERE tagType = '{tagType}' AND audioFile = '{filepath}';
                """
                logger.debug(f"query = {query}")
                c.execute(query)
            conn.commit()
        except sqlite3.OperationalError:
            logger.error("Fatal error when executing SQL")
            return None
        finally:
            c.close()
            conn.close()
        self.sigRemoveFinished.emit(returnedData)


class AudioTagController(QObject):

    sigSetAudiotagPath = Signal(object)
    sigWriteToDatabase = Signal(object, object, object)
    sigRemoveFromDatabase = Signal(object, object)
    sigDatabaseInteractionFinished = Signal()

    def __init__(self, parent: MainController) -> None:
        super().__init__(parent)
        self.fileProxyModel = parent._model.fileProxyModel
        self.fileSystemModel = parent._model.fileSystemModel
        self.validTags = {"skip", "flag"}
        self.thread = AudiotagCommunicationThread()
        self.sigWriteToDatabase.connect(self.thread.writeToDatabase)
        self.sigRemoveFromDatabase.connect(self.thread.removeFromDatabase)
        self.sigSetAudiotagPath.connect(self.thread.setAudiotagPath)
        self.thread.sigAddFinished.connect(self.postProccessAddEntries)
        self.thread.sigRemoveFinished.connect(self.postProcessRemoveEntries)
        self.destroyed.connect(self.thread.quit)
        self.thread.start()

    @Slot(object)
    def postProccessAddEntries(
        self, data: List[Tuple[AudiotagEntry, QModelIndex]]
    ) -> None:
        for entry, index in data:
            self.updateDataStructures(
                entry.tagType, entry.audioFile, remove=False, entry=entry
            )
            self.updateViews(index, entry.audioFile)
        self.sigDatabaseInteractionFinished.emit()
        return None

    @Slot(object)
    def postProcessRemoveEntries(
        self, data: List[Tuple[str, str, QModelIndex]]
    ) -> None:
        for tagType, filepath, index in data:
            self.updateDataStructures(tagType, filepath, remove=True)
            self.updateViews(index, filepath)
        self.sigDatabaseInteractionFinished.emit()
        return None

    def updateViews(self, index: QModelIndex, path: str) -> None:
        if index.model() is self.fileSystemModel:
            index.model().dataChanged.emit(index, index)
        else:
            df = index.model().df
            for row in df[df["original"] == path].index.to_numpy(dtype=int):
                tagIndex = index.model().createIndex(row, 0)
                index.model().dataChanged.emit(tagIndex, tagIndex)
        return None

    def updateDataStructures(
        self,
        tagType: str,
        path: str,
        remove: bool,
        entry: Optional[AudiotagEntry] = None,
    ) -> None:
        model = self.fileProxyModel.sourceModel()
        if remove:
            del model.audiotagData[path][tagType]
        else:
            if entry is None:
                raise RuntimeError("If not removing, an entry must be provided")
            model.audiotagData[path].update({tagType: entry})
        df = model.df
        df.loc[df["original"] == path, tagType] = not remove
        return None

    def removeFromDatabase(self, indexes: List[QModelIndex], tagType: str) -> None:
        if not self.checkWritePermissions():
            tagDialog = QApplication.instance().focusWidget().parent()  # noqa: F821
            tagDialog.close()
            raise Exception(
                f"audiotagdb3 Write Unsuccessful, No Write Permissions to {self.audioTagPath.as_posix()}"
            )
        else:
            self.checkTag(tagType)
            if not indexes:
                logger.warning(f"No indexes selected to {tagType}")
                return None

            pairs = self.matchIndexesToPaths(indexes)
            if not pairs:
                logger.warning(f"No paths identified to {tagType}")
                return None
            self.sigSetAudiotagPath.emit(self.audioTagPath)
            self.sigRemoveFromDatabase.emit(pairs, tagType)

    def addToDatabase(
        self, indexes: List[QModelIndex], data: Dict[str, str], tagType: str
    ) -> None:
        if not self.checkWritePermissions():
            tagDialog = QApplication.instance().focusWidget().parent()  # noqa: F821
            tagDialog.close()
            raise Exception(
                f"audiotagdb3 Write Unsuccessful, No Write Permissions to {self.audioTagPath.as_posix()}"
            )
        else:
            self.checkTag(tagType)

            if not indexes:
                logger.warning(f"No indexes selected to {tagType}")
                return None
            pairs = self.matchIndexesToPaths(indexes)
            if not pairs:
                logger.warning(f"No paths identified to {tagType}")
                return None
            self.sigSetAudiotagPath.emit(self.audioTagPath)
            self.sigWriteToDatabase.emit(pairs, data, tagType)

    def matchIndexesToPaths(self, indexes: List[QModelIndex]) -> Dict[str, QModelIndex]:
        pairs: Dict[str, QModelIndex] = {}
        for index in indexes:
            if index.model() is self.fileProxyModel:
                index = self.fileProxyModel.mapToSource(index)
            if index.model() is self.fileSystemModel:
                # fileSystem model case
                fileInfo = index.model().fileInfo(index)
                if fileInfo.isDir():
                    # in case index represents a directory...
                    nChildren = index.model().rowCount(index)
                    for i in range(nChildren):
                        childIndex = index.child(i, 0)
                        fileInfo = index.model().fileInfo(childIndex)
                        if fileInfo.isDir():
                            continue
                        networkPath = self.determineAudioFilePath(
                            childIndex, self.getNetworkFilePath
                        )
                        pairs[networkPath] = childIndex
                else:
                    networkPath = self.determineAudioFilePath(
                        index, self.getNetworkFilePath
                    )
                    pairs[networkPath] = index
            else:
                networkPath = self.determineAudioFilePath(
                    index, self.getNetworkFilePath
                )
                pairs[networkPath] = index
        return pairs

    @staticmethod
    def determineAudioFilePath(
        index: QModelIndex, pathGetter: Callable[[Path], Optional[Path]]
    ) -> str:
        row = index.model().currentSelection(index)
        path = Path(row["original"])
        newpath = pathGetter(path)
        if newpath is None:
            logger.warning(
                f"Could not determine 'remote path' of: {path.as_posix()} return original path"
            )
            return path.as_posix()
        else:
            logger.info(f"Determined {path.as_posix()} maps to {newpath.as_posix()}")
            return newpath.as_posix()

    def checkWritePermissions(self) -> bool:
        if self.audioTagPath.exists():
            return os.access(self.audioTagPath, os.W_OK)
        else:
            return os.access(self.audioTagPath.parent, os.W_OK)

    @property
    def audioTagPath(self) -> Path:
        audioTagPath = self.parent().fileParser.thread.audioTagPath
        return audioTagPath

    @property
    def getNetworkFilePath(self) -> Callable[[Path], Optional[Path]]:
        return self.parent()._model.pathMapper.getNetworkFilepath

    def checkTag(self, tag: str) -> None:
        if tag not in self.validTags:
            raise ValueError(f"Unknown tag: {tag}. Valid set: {self.validTags}.")
