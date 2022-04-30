from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from qtpy.QtCore import QObject

from ..Utilities.PathMapper import PathMapper
from .FileSystemModel import FileSystemModel
from .SortFilterProxyModel import SortFilterProxyModel

if TYPE_CHECKING:
    from qtpy.QtCore import QModelIndex
    from signalworks.tracking import Wave


logger = logging.getLogger(__name__)


class MainModel(QObject):
    def __init__(self) -> None:
        super().__init__()
        self.pathMapper = PathMapper(self)
        self.fileProxyModel = SortFilterProxyModel(self)
        self.fileSystemModel = FileSystemModel(self)

        self.currentWaveform: Optional[Wave] = None
        self._currentWorkingDirectory: Optional[Path] = None

    def index(self, x: int, y: int = 0) -> QModelIndex:
        """Method return a QModelIndex based on x and y positions

        Parameters
        ----------
        x : int
            row to create a QModelIndex from
        y : int, optional
            column to create a QModelIndex from, by default 0

        Returns
        -------
        QModelIndex
            Used for manually selected entries
        """
        return self.fileProxyModel.index(x, y)

    @property
    def currentWorkingDirectory(self) -> Optional[Path]:
        return Path(self.fileSystemModel.rootPath())

    @currentWorkingDirectory.setter
    def currentWorkingDirectory(self, dirPath: Optional[Path]) -> None:
        if dirPath is None:
            self.fileSystemModel.setRootPath("")
        elif dirPath.exists():
            networkPath = self.pathMapper.getNetworkFilepath(dirPath)
            self.fileSystemModel.setRootPath(
                networkPath.as_posix()
                if networkPath is not None
                else dirPath.as_posix()
            )
        else:
            logger.error(
                f"How did you set the working directory ({dirPath.as_posix()})to a directory that doesn't exist?"
            )
            self.fileSystemModel.setRootPath("")
        return None
