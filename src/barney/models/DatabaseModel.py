from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Dict, Optional, Union

import numpy as np
import pandas as pd
from qtpy.QtCore import QAbstractTableModel, QModelIndex, Qt

from .DataFrameInterface import DataFrameInterface

if TYPE_CHECKING:
    from qtpy.QtWidgets import QWidget

logger = logging.getLogger(__name__)


class DatabaseModel(QAbstractTableModel, DataFrameInterface):
    def __init__(self, parent: QWidget = None) -> None:
        DataFrameInterface.__init__(self)
        QAbstractTableModel.__init__(self)
        self.entryCount = 0  # used for fetchMore compatability

    def rowCount(self, parent: QModelIndex) -> int:
        if parent.isValid():
            return 0
        return self.entryCount

    def columnCount(self, parent: QModelIndex) -> int:
        if parent.isValid():
            return 0
        return 1

    def data(
        self, index: QModelIndex, role: int = Qt.DisplayRole
    ) -> Optional[Union[str, int, float]]:
        row = index.row()
        dfRow = self.df.iloc[row]
        key = dfRow["key"]
        if role == Qt.DisplayRole:
            return self.df.iloc[row]["filename"]
        # What the tooltip should display
        elif role == Qt.ToolTipRole:
            columnsOfInterest = [
                "key",
                "class",
                "snr",
                "transcription",
                "order",
                "aggscore",
            ]
            contents = [
                f"{columnName} = {self.sourceData[key].get(columnName, 'None')}"
                for columnName in columnsOfInterest
            ]
            contents.append(f"AggScore = {dfRow['aggscore']}")
            audioTag = self.audiotagData.get(self.df.iloc[row]["filepath"])
            if audioTag:
                for info in audioTag.values():
                    contents.append("\n")
                    contents.append(f"Audiotag = {info.tagType}")
                    contents.append(f"Labeled by = {info.tagger}")
                    contents.append(f"Reason = {info.reason[1:-1]}")
                    contents.append(f"Comments = {info.comment[1:-1]}")
            return "\n".join(contents)

        return None

    def sort(
        self, column: int, order: int = Qt.AscendingOrder
    ) -> None:  # pragma: no cover
        logger.error("Not using Qt's Sort method, look at self.sortBy() instead")
        raise NotImplementedError

    def loadDatabase(
        self, contents: Dict[str, Dict[str, str]], df: pd.DataFrame
    ) -> None:
        self.df = df
        self.sourceData = contents

    def currentSelection(self, index: QModelIndex) -> pd.Series:
        return self.df.iloc[index.row()]

    def currentSourceData(self, index: QModelIndex) -> Dict[str, str]:
        if index.model() is not self:
            raise RuntimeError
        row = index.model().currentSelection(index)
        return self.sourceData[row["key"]]

    def fetchMore(self, parent: QModelIndex) -> None:
        if parent.isValid():
            return None

        remainder = self.df.shape[0] - self.entryCount

        # remaining rows that meet filter criteria
        chunkSize = 100
        remainingRowsMeetingFilterCriteria = np.all(
            self.filterMatrix[self.entryCount :, :], axis=1
        )
        chunkIndex = np.searchsorted(
            np.cumsum(remainingRowsMeetingFilterCriteria), chunkSize
        )
        itemsToFetch = min(chunkIndex, remainder)
        if itemsToFetch <= 0:
            return None

        self.beginInsertRows(
            QModelIndex(), self.entryCount, self.entryCount + itemsToFetch - 1
        )
        self.entryCount += itemsToFetch
        self.endInsertRows()

    def canFetchMore(self, parent: QModelIndex) -> bool:
        if parent.isValid():
            return False
        return self.entryCount < self.df.shape[0]
