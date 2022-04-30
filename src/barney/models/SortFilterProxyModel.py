from __future__ import annotations

import logging
from collections import defaultdict
from pathlib import Path
from timeit import default_timer as timer
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
from qtpy.QtCore import QModelIndex, QSortFilterProxyModel, Qt, Slot

# from .CompletionModel import CompletionModel
from .DatabaseModel import DatabaseModel

if TYPE_CHECKING:
    from typing import Callable, DefaultDict, Dict, List, Tuple

    from ..Utilities.parsers import AudiotagEntry
    from .model import MainModel

logger = logging.getLogger(__name__)


class SortFilterProxyModel(QSortFilterProxyModel):
    def __init__(self, parent: MainModel) -> None:
        super().__init__(parent)
        self.setSortRole(Qt.UserRole)
        self.regexColumns: Dict[str, str] = {}
        self.filterColumns: Dict[str, Tuple[str, str]] = {}
        self.setDynamicSortFilter(False)

    @property
    def df(self) -> pd.DataFrame:
        return self.sourceModel().df

    @property
    def audiotagData(self) -> Dict[str, Dict[str, AudiotagEntry]]:
        return self.sourceModel().audiotagData

    def currentSelection(self, index: QModelIndex) -> pd.Series:
        if index.model() is self:
            index = self.mapToSource(index)
        if not index.isValid():
            raise RuntimeError
        row = index.model().currentSelection(index)
        return row

    def currentSourceData(self, index: QModelIndex) -> Dict[str, str]:
        if self.sourceModel() is None:
            return {}

        if index.model() is self:
            index = self.mapToSource(index)

        entry = index.model().currentSourceData(index)
        if entry is None:
            entry = {}
        return entry

    def resetDatabaseModel(self) -> None:
        logger.info("Reset Base Model Called")
        self.setSourceModel(DatabaseModel(self))

    @Slot(defaultdict)
    def loadAudiotags(
        self, contents: DefaultDict[str, Dict[str, AudiotagEntry]]
    ) -> None:
        self.sourceModel().audiotagData = contents
        self.sourceModel().updateAudiotags()

    def addEntries(self, fileList: List[Path]) -> None:
        self.sourceModel().addEntries(fileList)
        self.dataChanged.emit(QModelIndex(), QModelIndex())
        self.layoutChanged.emit()

    def sortBy(self, sortByColumns: Dict[str, bool]) -> None:
        """Method receives a list of of tuples.  First element of the tuple is the
        name of the column to sort by, second element indicates if the sort should
        be in ascending order

        Arguments:
            sortByColumns {List[Tuple[str, bool]]} -- column name, ascending order

        Returns:
            None -- Method does not return anything
        """
        startTime = timer()
        self.layoutAboutToBeChanged.emit()

        columns, ascending = zip(*sortByColumns.items())

        # store persistent indexes
        oldIndexList = self.persistentIndexList()
        oldIds = self.sourceModel().df.index.copy()
        self.sourceModel().df.sort_values(
            by=list(columns), ascending=list(ascending), inplace=True
        )
        # Updating persistent indexes
        newIndexList = [
            self.index(
                self.df.index.get_loc(oldIds[index.row()]),
                index.column(),
                index.parent(),
            )
            for index in oldIndexList
        ]

        self.changePersistentIndexList(oldIndexList, newIndexList)
        self.layoutChanged.emit()
        self.dataChanged.emit(QModelIndex(), QModelIndex())
        finishTime = timer()
        logger.info(
            f"Sort operation on {', '.join(columns)} column(s) and {self.df.shape[0]}"
            f" rows took {finishTime - startTime:{5}.{2}} seconds to complete"
        )
        self.invalidate()

    def filterBy(self, filterByColumns: Dict[str, Tuple[str, float]]) -> None:
        operationMapping: Dict[str, Callable[[np.ndarray, float], np.ndarray]] = {
            "!=": np.not_equal,
            "==": np.equal,
            ">": np.greater,
            ">=": np.greater_equal,
            "=>": np.greater_equal,
            "<": np.less,
            "<=": np.less_equal,
            "=<": np.less_equal,
        }
        filterMatrix = self.sourceModel().filterMatrix
        filterMatrix.fill(True)
        for columnIndex, columnName in enumerate(self.df.columns):
            if columnName in filterByColumns.keys():
                criteria = filterByColumns[columnName]
                logger.info(f"Filtering {columnName} by {criteria[0]} {criteria[1]}")
                array = self.df.values[:, columnIndex]
                filterMatrix[:, columnIndex] = operationMapping[criteria[0]](
                    array, criteria[1]
                )
        self.invalidate()
        self.sourceModel().fetchMore(QModelIndex())

    def regexBy(self, regexByColumns: Dict[str, str]) -> None:
        # not the most efficient looping mechanism :/
        filterMatrix = self.sourceModel().filterMatrix
        for columnIndex, columnName in enumerate(self.df.columns):
            if columnName in regexByColumns:
                filterMatrix[:, columnIndex] = (
                    self.df[columnName]
                    .str.contains(regexByColumns[columnName], case=False, regex=True)
                    .values
                )
                logger.debug(
                    f"Filtering {columnName} by regex match "
                    f"of {regexByColumns[columnName]} "
                    f"with {filterMatrix[:, columnIndex].sum()} matches"
                )
        self.invalidate()

    def filterAcceptsRow(self, sourceRow: int, parent: QModelIndex) -> bool:
        # filterMatrix is of shape (entries, filter-criteria-met)
        # to determine if a row should be shown, it needs to have all values
        # be true for any given row
        try:
            filterMatrix = self.sourceModel().filterMatrix
            show = bool(np.all(filterMatrix[sourceRow, :]))
        except IndexError:
            show = True
        return show
