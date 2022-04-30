from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

from qtpy.QtCore import QObject

if TYPE_CHECKING:
    from typing import List, Set

    from qtpy.QtCore import QModelIndex
    from signalworks.tracking import Wave

    from barney.controllers.controller import MainController


logger = logging.getLogger(__name__)


class CacheController(QObject):
    def __init__(self, parent: MainController) -> None:
        super().__init__(parent)
        self.cacheBlacklist: Set[Path] = set()

    @lru_cache(maxsize=64)
    def getTrackCache(self, pathObj: Path) -> Wave:
        logger.debug(f"{pathObj.as_posix()} not found in cache, loading from file.")
        return self.parent().load_audio(pathObj)

    def refreshTracks(self, indices: List[QModelIndex]) -> None:
        self.clearGetTrackCache()
        self.parent().selectIndex(indices[0])

    def clearGetTrackCache(self) -> None:
        logger.warning("Clearing getTrack cache...")
        self.getTrackCache.cache_clear()

    def allowCaching(self, indices: List[QModelIndex]) -> None:
        fileProxyModel = self.parent()._model.fileProxyModel
        for index in indices:
            index = fileProxyModel.mapFromSource(index)
            path = Path(
                self.parent()._model.fileProxyModel.currentSelection(index)["filepath"]
            )
            if path is None:
                continue
            if path in self.cacheBlacklist:
                self.cacheBlacklist.remove(path)
                self.clearGetTrackCache()  # avoid previously cached versions
            logger.debug(f"Caching allowed for {path}")

    def prohibitCaching(self, indices: List[QModelIndex]) -> None:
        for index in indices:
            sourceData = index.model().currentSourceData(index)
            if not sourceData:
                continue
            path = Path(sourceData["filename"])
            self.cacheBlacklist.add(path)
            logger.debug(f"Caching not allowed for {path.as_posix()}")

    def isBlacklisted(self, index: QModelIndex) -> bool:
        sourceData = index.model().currentSourceData(index)
        if not sourceData:
            # this occurs when QFileSystemModel is not finished loading the directory
            return False
        else:
            path = Path(sourceData["filename"])
            return path in self.cacheBlacklist if path else True
